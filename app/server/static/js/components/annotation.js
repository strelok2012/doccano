export default {
    template: `<div class="tag" :style="computedStyle">
      <button class="delete is-small"
      style="z-index: 101; margin-bottom: .5rem;"
      @click="removeLabel"></button>
    </div>`,
    props: {
      annotationElement: Object,
      id2label: Object
    },
    computed: {
      computedStyle () {
        const elements = this.annotationElement.elements
        const label = this.id2label[this.annotationElement.annotation.label]
        const bbStart = elements[0].parentNode.getBoundingClientRect()
        const bbEnd = elements[1].parentNode.getBoundingClientRect()
        const padding = 30;
        return {
          backgroundColor: label.background_color,
          position: 'absolute',
          left: `${elements[0].parentNode.offsetLeft - padding / 2}px`,
          top: `${elements[0].parentNode.offsetTop}px`,
          height: `${bbEnd.bottom - bbStart.top}px`,
          width: `${bbStart.width + padding}px`,
          alignItems: 'center',
          justifyContent: 'flex-end'
        }
      }
    },
    methods: {
      removeLabel () {
        this.$emit('remove-label', this.annotationElement.annotation)
      }
    }
  }