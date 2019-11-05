import Vue from 'vue';
import HTTP from './http';
import * as bulmaToast from 'bulma-toast';

import annotationMixin from './mixin';

Vue.use(require('vue-shortkey'), {
    prevent: ['input', 'textarea'],
  });

const vm = new Vue({
  el: '#mail-app',
  delimiters: ['[[', ']]'],
  mixins: [annotationMixin],
  data () {
      return {
          geckoReady: false,
          fileName: null,
          filePath: null,
          docNumber: 0
      }
  },
  created () {
    
  },
  async mounted () {
    window.document.addEventListener('geckoSave', (e) => {
        this.saveAudioAnnotation(e.detail)
    }, false)
    const geckoRes = await this.loadGecko()
    this.geckoReady = geckoRes
    this.tryInit()
  },
  methods: {
      tryInit () {
        if (this.docs && this.docs.length && this.geckoReady) {
          this.loadDoc(this.docs[this.docNumber])
        }
      },
      loadDoc (doc) {
        const url = doc.text
        const urlSplit = url.split('/')
        const fileName = urlSplit[urlSplit.length - 1]

        const ctms = doc.annotations
        const eventData = {
            audio: {
                url,
                fileName
            }
        }
        if (ctms && ctms.length) {
            eventData.ctms = ctms
        }

        console.log('load doc')
        const event = new CustomEvent('loadExternal', {
            detail: eventData
         })

        this.fileName = fileName
        this.filePath = url
        this.$refs.gecko.contentDocument.dispatchEvent(event)
      },
      async saveAudioAnnotation (data) {
        const doc = this.docs[this.docNumber]
        const docId = doc.id;
        const payload = {
          file_path: this.filePath,
          file_name: data.filename,
          data: data.data
        };
        await HTTP.post(`docs/${docId}/annotations/`, payload).then((response) => {
          // this.annotations[pageNumber].push(response.data);
        });
        bulmaToast.toast({
            message: `Successfully saved to DB.`,
            type: 'is-success',
            position: 'top-center',
        });
      },
      async loadGecko () {
        return new Promise((resolve, reject) => {
            window.document.addEventListener('geckoReady', () => {
                resolve(true)
            }, false)
        })
      },
      nextDoc () {
        this.docNumber = this.docNumber + 1
        this.loadDoc(this.docs[this.docNumber])
      },
      prevDoc () {
        this.docNumber = this.docNumber - 1
        this.loadDoc(this.docs[this.docNumber])
      }
  },
  watch: {
      docs (newValue) {
        this.tryInit()
      }
  }
});
