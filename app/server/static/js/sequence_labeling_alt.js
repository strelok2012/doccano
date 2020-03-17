import Vue from 'vue';
import * as bulmaToast from 'bulma-toast';

import annotationMixin from './mixin';
import HTTP from './http';
import simpleShortcut from './filter';

Vue.use(require('vue-shortkey'), {
  prevent: ['input', 'textarea'],
});

Vue.filter('simpleShortcut', simpleShortcut);

const transformAnnotation = (a) => {
  const { id, label, prob } = a
  if (a.additional_data) {
    try {
      const data = JSON.parse(a.additional_data)
      const { start_offset, end_offset } = data
      return {
        start_offset,
        end_offset,
        id,
        label,
        prob
      }
    } catch (e) {
      return {
        id,
        label,
        prob
      }
    }
  }
}

Vue.component('annotator', {
  template: `<div>
                    <span class="text-sequence"
                         v-for="r in chunks"
                         v-if="id2label[r.label]"
                         v-bind:class="{tag: id2label[r.label].text_color, 'text-sequence--sentence': sentenceLabeling}"
                         v-bind:style="{ color: id2label[r.label].text_color, backgroundColor: id2label[r.label].background_color }"
                    >{{ text.slice(r.start_offset, r.end_offset) }}<button class="delete is-small"
                                         v-if="id2label[r.label].text_color"
                                         @click="removeLabel(r)"></button></span>
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

      if (this.sentenceLabeling) {
        for (let i = 0; i < this.sentences.length; i++) {
          const s = this.sentences[i]
          if (i > 0) {
            const prev = this.sentences[i - 1]
            if (this.endOffset === s.start_offset) {
              this.endOffset = prev.end_offset
            }
          }
          
          if (this.startOffset >= s.start_offset && this.startOffset <= s.end_offset) {
            this.startOffset = s.start_offset
          }

          if (this.endOffset >= s.start_offset && this.endOffset <= s.end_offset) {
            this.endOffset = s.end_offset
          }
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

    sentences() {
      const splited = this.text.split('\n')
      const acc = []
      return splited.reduce((acc, current) => {
        let offset = 0
        if (acc.length) {
          const last = acc[acc.length - 1]
          offset = last.end_offset + 1
        }

        acc.push({
          start_offset: offset,
          end_offset: current.length + offset
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
});

const uuidv4 = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

const vm = new Vue({
  el: '#mail-app',
  delimiters: ['[[', ']]'],
  mixins: [annotationMixin],
  data () {
    return {
      toDelete: [],
      toAdd: [],
      originalAnnotations: null
    }
  },
  computed: {
    approveDisabled () {
      if (this.mlMode) {
        return !this.currentAnnotations.length
      }
      return !this.toDelete.length && !this.toAdd.length
    }
  },
  methods: {
    annotate(labelId) {
      this.$refs.annotator.addLabel(labelId);
    },

    addLabel(annotation) {
      annotation.id = uuidv4()
      this.currentAnnotations.push(annotation)
      this.toAdd.push(annotation)
    },

    removeLabel(annotation) {
      const index = this.currentAnnotations.findIndex(a => a.id === annotation.id)
      this.currentAnnotations.splice(index, 1)
      if (Number.isInteger(annotation.id)) {
        this.toDelete.push(annotation)
      } else {
        const toAddIndex = this.toAdd.findIndex(a => a.id === annotation.id)
        this.toAdd.splice(toAddIndex, 1)
      }
    },

    async approve () {
      const docId = this.docs[this.pageNumber].id

      if (this.mlMode) {        
        for (let i = 0; i < this.currentAnnotations.length; i++) {
          const a = this.currentAnnotations[i]
          const res = await HTTP.post(`docs/${docId}/annotations/`, a)
          this.annotations[this.pageNumber].push(res.data)
        }

        this.toAdd = []
        this.toDelete = []

        this.rebuildCurrentAnnotations(this.pageNumber)
      } else {
        if (this.toAdd.length || this.toDelete.length) {
          for (let i = 0; i < this.toAdd.length; i++) {
            const a = this.toAdd[i]
            const res = await HTTP.post(`docs/${docId}/annotations/`, a)
            this.annotations[this.pageNumber].push(res.data)
          }
  
          this.toAdd = []
  
          for (let i = 0; i < this.toDelete.length; i++) {
            const a = this.toDelete[i]
            await HTTP.delete(`docs/${docId}/annotations/${a.id}`)
          }
  
          this.toDelete = []
        }
      }

      bulmaToast.toast({
        message: `Successfully saved.`,
        type: 'is-success',
        position: 'top-center'
      });
    },

    entityPositionsChange (val) {
    }
  }
});