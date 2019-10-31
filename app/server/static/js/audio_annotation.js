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
          filePath: null
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

    this.loadDoc(this.docs[this.pageNumber])
  },
  methods: {
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
        const event = new CustomEvent('loadExternal', {
            detail: eventData
         })

        this.fileName = fileName
        this.filePath = url
        this.$refs.gecko.contentDocument.dispatchEvent(event)
      },
      async saveAudioAnnotation (data) {
        const doc = this.docs[this.pageNumber]
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
      }
  },
  watch: {
      geckoReady (newValue) {
          console.log('IS READY')
      },
      docs (newValue) {
          console.log('docs', newValue)
      }
  }
});
