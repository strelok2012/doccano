<template>
    <div style="position: relative">
      <TextAnnotation v-for="(r, index) in chunks" :element="r" :key="index" :labels="id2label" :text="text" @remove-label="removeLabel"/>
    </div>
</template>

<script>
import TextAnnotation from './TextAnnotation'

import { transformAnnotation, getRangeSelectedNodes, inRange } from '../utils'

export default {
    props: {
      labels: Array, // [{id: Integer, color: String, text: String}]
      text: String,
      entityPositions: Array
    },
    components: {
      TextAnnotation
    },
    data() {
      return {
        startOffset: 0,
        endOffset: 0,
        currentSelection: null,
        added: []
      };
    },
    mounted () {
      document.addEventListener('selectionchange', this.selectionChange.bind(this))
  
      this.$emit('entity-positions-change', this.entityPositions)
    },
  
    destroy () {
      document.addEventListener('selectionchange', this.selectionChange.bind(this))
    },
  
    methods: {
      selectionChange () {
        const selection = document.getSelection()
        if (this.$el.contains(selection.focusNode)) {
          this.currentSelection = selection
          this.setSelectedRange()
        }
      },

      setSelectedRange(e) {
        let start;
        let end;
        if (window.getSelection) {
          const range = window.getSelection().getRangeAt(0);
          const preSelectionRange = range.cloneRange();
          preSelectionRange.selectNodeContents(this.$el);
          preSelectionRange.setEnd(range.startContainer, range.startOffset);
          const preselectionText = preSelectionRange.toString().split('\n').filter(t => t.trim().length).join('')
          const rangeString = range.toString().split('\n').filter(t => t.trim().length).join('')
          start = preselectionText.length;
          end = start + rangeString.length;
        } else if (document.selection && document.selection.type !== 'Control') {
          const selectedTextRange = document.selection.createRange();
          const preSelectionTextRange = document.body.createTextRange();
          preSelectionTextRange.moveToElementText(this.$el);
          preSelectionTextRange.setEndPoint('EndToStart', selectedTextRange);
          start = preSelectionTextRange.text.length;
          end = start + selectedTextRange.text.length;
        }

        if (this.overlapedAnnotations.length) {
          const delta = this.overlapedAnnotations.reduce((accumulator, currentValue) => {
            if (start >= currentValue.end) {
              return accumulator + (currentValue.end - currentValue.start)
            }

            return accumulator
          }, 0);

          start -= delta
          end -= delta
        }

        this.startOffset = start;
        this.endOffset = end;
      },
  
      validRange(labelId) {
        if (this.startOffset === this.endOffset) {
          return false;
        }
        if (this.startOffset > this.text.length || this.endOffset > this.text.length) {
          return false;
        }
        if (this.startOffset < 0 || this.endOffset < 0) {
          return false;
        }

        const startElement = this.sortedEntityPositions.filter(ep => {
          return this.startOffset >= ep.start_offset && this.startOffset < ep.end_offset
        }).sort((a, b) => {
          return a.start_offset - b.start_offset
        }).pop()

        const endElement = this.sortedEntityPositions.filter(ep => {
          return this.endOffset > ep.start_offset && this.endOffset <= ep.end_offset
        }).sort((a, b) => {
          return a.start_offset - b.start_offset
        }).pop()

        /* don't allow to place same label in labeled text */
        if (startElement && startElement.label === labelId) {
          return false
        }

        return true;
      },
  
      resetRange() {
        this.startOffset = 0;
        this.endOffset = 0;
      },
  
      addLabel(labelId) {
        if (this.validRange(labelId)) {
          const label = {
              additional_data: JSON.stringify({
                start_offset: this.startOffset,
                end_offset: this.endOffset
              }),
              label: labelId,
            };
          
          this.$emit('add-label', label);
        }
      },
  
      removeLabel(index) {
        this.$emit('remove-label', index);
      },
  
      makeLabel(startOffset, endOffset) {
        const label = {
          id: 0,
          label: -1,
          start_offset: startOffset,
          end_offset: endOffset,
        };
        return label;
      },

      prepareTree (tree, left, right) {
        const res = [];
        for (let i = 0; i < tree.length; i++) {
          const e = tree[i];
          const l = this.makeLabel(left, e.start_offset);
          res.push(l);
          e.childs = e.childs.length ? this.prepareTree(e.childs, e.childs[0].start_offset, e.end_offset) : []
          res.push(e);
          left = e.end_offset;
        }
        const l = this.makeLabel(left, right);
        res.push(l);
  
        return res;
      },


      processEp (position)  {
        const ret = { ...position, childs: [] }
        this.sortedEntityPositions.filter((ep) => ep.start_offset >= position.start_offset && ep.end_offset <= position.end_offset && ep.id !== position.id).forEach(ep => {
          if (!this.added.includes(ep.id)) {
            this.added.push(ep.id)
            ret.childs.push(this.processEp(ep, this.sortedEntityPositions))
          }
        })

        return ret
      },

      chunkTree () {
        const ret = []
        this.sortedEntityPositions.forEach(ep => {
          if (!this.added.includes(ep.id)) {
            this.added.push(ep.id)
            ret.push(this.processEp(ep, this.sortedEntityPositions))
          }
        })
        return ret
      }
    },
  
    watch: {
      entityPositions(val) {
        this.added = []
        this.resetRange();
        this.$emit('entity-positions-change', val)
      },
    },
  
    computed: {
      sortedEntityPositions() {
        const ret = this.entityPositions.map((ep) => {
          if (ep.start_offset || ep.end_offset) {
            return ep
          }
          return transformAnnotation(ep)
        }).sort((a, b) => a.start_offset - b.start_offset)
        return ret;
      },
  
      chunks() {
        return this.prepareTree(this.chunkTree(this.sortedEntityPositions), 0, this.text.length)
      },
  
      id2label() {
        let id2label = {};
        // default value;
        id2label[-1] = {
          text_color: '',
          background_color: '',
        };
        for (let i = 0; i < this.labels.length; i++) {
          const label = this.labels[i];
          id2label[label.id] = label;
        }
        return id2label;
      },

      overlapedAnnotations () {
        const ret = []
        const compared = []
        this.sortedEntityPositions.forEach((cmpA) => {
          this.sortedEntityPositions.forEach((cmpB) => {
            if (cmpA !== cmpB && !compared.includes(cmpA)) {
              if (cmpB.start_offset > cmpA.start_offset && cmpB.start_offset < cmpA.end_offset) {
                if (cmpB.end_offset > cmpA.end_offset) {
                  compared.push(cmpA)
                  ret.push({
                    start: cmpB.start_offset,
                    end: cmpA.end_offset
                  })
                }
              }
            }
          })
        })
        return ret
      }
    },
}
</script>