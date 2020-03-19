import { transformAnnotation, getRangeSelectedNodes } from '../utils'

export default {
    template: `<div style="position: relative">
                  <template v-if="sentenceLabeling">
                    <div class="sentence-labeling">
                      <div class="sentence-labeling__sentence" v-for="(sentence, index) in sentences" v-if="sentence.text.length" :key="index">
                        <div class="sentence-labeling__speaker">
                          <p>No speaker</p>
                        </div>
                        <div class="sentence-labeling__text" :class="{ 'sentence-labeling__text--empty': !sentence.text.length }" :style="getSentenceStyle(sentence)">
                          <p style="position: relative;" v-if="sentence.text.length" :ref="getRef(sentence.index)" :data-index="sentence.index">{{ sentence.text }}</p>
                        </div>
                      </div>
                    </div>
                    <annotation v-for="(ae, index) in annotationsWithElements" v-if="id2label[ae.annotation.label]" :annotation-element="ae" :id2label="id2label" :key="index" @remove-label="removeLabel"/>
                    </template>
                  <template v-else>
                    <span class="text-sequence"
                          v-for="r in chunks"
                          v-if="id2label[r.label]"
                          v-bind:class="{tag: id2label[r.label].text_color, 'text-sequence--sentence': sentenceLabeling}"
                          v-bind:style="{ color: id2label[r.label].text_color, backgroundColor: id2label[r.label].background_color }"
                    >{{ text.slice(r.start_offset, r.end_offset) }}<button class="delete is-small"
                                          v-if="id2label[r.label].text_color"
                                          @click="removeLabel(r)"></button></span>
                  </template>
              </div>`,
    props: {
      labels: Array, // [{id: Integer, color: String, text: String}]
      text: String,
      entityPositions: Array, // [{'startOffset': 10, 'endOffset': 15, 'label_id': 1}],
      sentenceLabeling: Boolean
    },
    data() {
      return {
        startOffset: 0,
        endOffset: 0,
        currentSelection: null,
        selectedSentences: [],
        annotationsWithElements: []
      };
    },
    mounted () {
      document.addEventListener('selectionchange', this.selectionChange.bind(this))
  
      this.computeAnnotationsWithElements()
  
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
        if (!this.sentenceLabeling) {
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
        } else {
          const range = window.getSelection().getRangeAt(0)
          let nodes = getRangeSelectedNodes(range)
          let last = nodes[nodes.length - 1]
          while (last.nodeType !== Node.TEXT_NODE) {
            nodes.pop()
            last = nodes[nodes.length - 1]
          }
  
          this.selectedSentences = nodes.filter(n => n.nodeType === Node.TEXT_NODE).map(n => n.parentNode).filter(n => n.tagName === 'P' && n.parentNode.classList.contains('sentence-labeling__text'))
        }
      },
  
      validRange() {
        if (this.sentenceLabeling) {
          const start = this.selectedSentences[0]
          const end = this.selectedSentences[this.selectedSentences.length - 1]
  
          const startIndex = parseInt(start.getAttribute('data-index'))
          const endIndex = parseInt(end.getAttribute('data-index'))
  
          if (Number.isInteger(startIndex) && Number.isInteger(endIndex)) {
            const startSentence = this.sentences[startIndex]
            const endSentence = this.sentences[endIndex]
            
            for (let i = 0; i < this.sortedEntityPositions.length; i++) {
              const ep = this.sortedEntityPositions[i]
              if (startSentence.start_offset === ep.start_offset || endSentence.end_offset === ep.end_offset || (ep.start_offset < startSentence.start_offset &&  ep.end_offset > endSentence.end_offset)) {
                return false
              }
            }
  
            return true
          }
          return false
        }
  
        if (this.startOffset === this.endOffset) {
          return false;
        }
        if (this.startOffset > this.text.length || this.endOffset > this.text.length) {
          return false;
        }
        if (this.startOffset < 0 || this.endOffset < 0) {
          return false;
        }
  
        for (let i = 0; i < this.entityPositions.length; i++) {
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
        }
        return true;
      },
  
      resetRange() {
        this.startOffset = 0;
        this.endOffset = 0;
      },
  
      addLabel(labelId) {
        if (this.validRange()) {
          let label
          if (this.sentenceLabeling) {
            const start = this.selectedSentences[0]
            const end = this.selectedSentences[this.selectedSentences.length - 1]
  
            const startIndex = parseInt(start.getAttribute('data-index'))
            const endIndex = parseInt(end.getAttribute('data-index'))
  
            if (Number.isInteger(startIndex) && Number.isInteger(endIndex)) {
              const startSentence = this.sentences[startIndex]
              const endSentence = this.sentences[endIndex]
              label = {
                additional_data: JSON.stringify({
                  start_offset: startSentence.start_offset,
                  end_offset: endSentence.end_offset
                }),
                label: labelId,
              };
            }
          } else {
            label = {
              additional_data: JSON.stringify({
                start_offset: this.startOffset,
                end_offset: this.endOffset
              }),
              label: labelId,
            };
          }
          
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
  
      getRef (idx) {
        return `paragraph_${idx}`
      },
  
      getSentenceStyle (s) {
        const ret = {}
        const ep = this.sortedEntityPositions.find(l => l.start_offset === s.start_offset || l.end_offset === s.end_offset || (s.start_offset > l.start_offset && s.end_offset < l.end_offset))
        if (ep && this.id2label[ep.label]) {
          ret.color = this.id2label[ep.label].text_color
        }
        return ret
      },
  
      computeAnnotationsWithElements () {
        this.$nextTick(() => {
          this.annotationsWithElements = this.sortedEntityPositions.map((ep) => {
            const sentenceIndexStart = this.sentences.findIndex(s => s.start_offset === ep.start_offset)
            const sentenceIndexEnd = this.sentences.findIndex(s => s.end_offset === ep.end_offset)
            return {
              annotation: ep,
              elements: [this.$refs[this.getRef(sentenceIndexStart)] && this.$refs[this.getRef(sentenceIndexStart)][0], this.$refs[this.getRef(sentenceIndexEnd)] && this.$refs[this.getRef(sentenceIndexEnd)][0]]
            }
          })
        })
      },
    },
  
    watch: {
      entityPositions(val) {
        this.resetRange();
        this.$emit('entity-positions-change', val)
        this.computeAnnotationsWithElements()
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
  
      sentences() {
        const splited = this.text.split('\n')
        const acc = []
        return splited.reduce((acc, current, index) => {
          let offset = 0
          if (acc.length) {
            const last = acc[acc.length - 1]
            offset = last.end_offset + 1
          }
  
          acc.push({
            start_offset: offset,
            end_offset: current.length + offset,
            text: current,
            index
          })
  
          return acc
        }, acc);
      },
  
      chunks() {
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