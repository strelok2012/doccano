import Vue from 'vue';
import * as bulmaToast from 'bulma-toast';

import annotationMixin from './mixin';

import annotation from './components/annotation'
import annotator from './components/annotator'

import HTTP from './http';
import simpleShortcut from './filter';

import { uuidv4 } from './utils'

Vue.use(require('./vue-shortkey'), {
  prevent: ['input', 'textarea'],
});

Vue.filter('simpleShortcut', simpleShortcut);

Vue.component('annotation', annotation)

Vue.component('annotator', annotator);

const vm = new Vue({
  el: '#mail-app',
  delimiters: ['[[', ']]'],
  mixins: [annotationMixin],
  data () {
    return {
      toDelete: [],
      toAdd: []
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
    }
  }
});