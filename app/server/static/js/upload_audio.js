import Vue from 'vue';
import axios from 'axios';
import * as bulmaToast from 'bulma-toast';

axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';

const vm = new Vue({
  el: '#mail-app',
  delimiters: ['[[', ']]'],
  data: {
    file: '',
    urlMode: false,
    activeTab: 1,
    selectedFormat: 'json',
    inputUrl: '',
    fail: [],
    success: 0,
    formats: {
      local: [
        {
          value: 'json',
          text: 'Upload a JSON file from your computer'
        }
      ],
      url: [
        {
          value: 'json_url',
          text: 'Upload a JSON file from URL'
        }
      ]
    }
  },
  methods: {
    handleFileUpload(e) {
      if (e.target.files && e.target.files.length) {
        this.file = e.target.files[0]
      }
    },
    async submit(e) {
      if (!this.file && this.activeTab === 1) {
        e.preventDefault()
        return
      }

      if ((!this.inputUrl || !this.inputUrl.length) && this.activeTab === 2) {
        e.preventDefault()
        return
      }


      e.preventDefault()
      this.fail = []
      this.success = 0
      const formData = new FormData()
      formData.set('file', this.file)
      formData.set('format', this.selectedFormat)
      formData.set('url', this.inputUrl)
      bulmaToast.toast({
        message: 'Processing...',
        type: 'is-info',
        position: 'top-center',
      })
      const result = await axios.post('', formData)
      this.fail = result.data.fail
      this.success = result.data.success
      bulmaToast.toast({
        message: 'Success!',
        type: 'is-success',
        position: 'top-center',
      })
    },
    setTab(tab) {
      this.activeTab = tab
      if (tab === 1) {
        this.selectedFormat = 'json'
      } else {
        this.selectedFormat = 'json_url'
      }
    }
  },
});
