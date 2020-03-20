<template>
    <div style="position: relative">
      <span class="text-sequence"
              v-for="(r, index) in chunks"
              :key="index"
              v-if="id2label[r.label]"
              v-bind:class="{tag: id2label[r.label].text_color}"
              v-bind:style="{ color: id2label[r.label].text_color, backgroundColor: id2label[r.label].background_color }"
      >{{ text.slice(r.start_offset, r.end_offset) }}<button class="delete is-small"
                              v-if="id2label[r.label].text_color"
                              @click="removeLabel(r)"></button></span>
      {{ chunks }}
    </div>
</template>

<script>
import { transformAnnotation, getRangeSelectedNodes } from '../utils'

const added = []

const processEp = (position, entityPositions) => {
  const ret = { ...position, childs: [] }
  entityPositions.filter((ep) => ep.start_offset >= position.start_offset && ep.end_offset <= position.end_offset && ep.id !== position.id).forEach(ep => {
    if (!added.includes(ep.id)) {
      ret.childs.push(processEp(ep, entityPositions))
      added.push(ep.id)
    }
  })

  return ret
}

const chunkTree = (entityPositions) => {
  const ret = []
  entityPositions.forEach(ep => {
    if (!added.includes(ep.id)) {
      ret.push(processEp(ep, entityPositions))
      added.push(ep.id)
    }
  })
  return ret
}

export default {
    props: {
      labels: Array, // [{id: Integer, color: String, text: String}]
      text: String,
      entityPositions: Array
    },
    data() {
      return {
        startOffset: 0,
        endOffset: 0,
        currentSelection: null
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
          start = preSelectionRange.toString().length;
          end = start + range.toString().length;
        } else if (document.selection && document.selection.type !== 'Control') {
          const selectedTextRange = document.selection.createRange();
          const preSelectionTextRange = document.body.createTextRange();
          preSelectionTextRange.moveToElementText(this.$el);
          preSelectionTextRange.setEndPoint('EndToStart', selectedTextRange);
          start = preSelectionTextRange.text.length;
          end = start + selectedTextRange.text.length;
        }
        this.startOffset = start;
        this.endOffset = end; 
      },
  
      validRange() {
        if (this.startOffset === this.endOffset) {
          return false;
        }
        if (this.startOffset > this.text.length || this.endOffset > this.text.length) {
          return false;
        }
        if (this.startOffset < 0 || this.endOffset < 0) {
          return false;
        }
  
        /* for (let i = 0; i < this.entityPositions.length; i++) {
          const e = this.entityPositions[i];
          try {
            const data = JSON.parse(e.additional_data)
            const start_offset = data.start_offset
            const end_offset = data.end_offset
            if ((start_offset <= this.startOffset) && (this.startOffset < end_offset)) {
              return false;
            }
            if ((start_offset < this.endOffset) && (this.endOffset < end_offset)) {
              return false;
            }
            if ((this.startOffset < start_offset) && (start_offset < this.endOffset)) {
              return false;
            }
            if ((this.startOffset < end_offset) && (end_offset < this.endOffset)) {
              return false;
            }
          } catch(e) {
          }
        } */
        return true;
      },
  
      resetRange() {
        this.startOffset = 0;
        this.endOffset = 0;
      },
  
      addLabel(labelId) {
        if (this.validRange()) {
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
      }
    },
  
    watch: {
      entityPositions(val) {
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
        const tree = chunkTree(this.sortedEntityPositions)
        console.log(tree)
        const res = [];
        let left = 0;
        for (let i = 0; i < this.sortedEntityPositions.length; i++) {
          const e = this.sortedEntityPositions[i];
          const l = this.makeLabel(left, e.start_offset);
          res.push(l);
          res.push(e);
          left = e.end_offset;
        }
        const l = this.makeLabel(left, this.text.length);
        res.push(l);
  
        return res;
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
    },
}
</script>