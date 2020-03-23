<template>
    <span v-if="labels[element.label] && chunkText.length" class="text-sequence"
            v-bind:class="{tag: labels[element.label].text_color}"
            v-bind:style="{ color: labels[element.label].text_color, backgroundColor: labels[element.label].background_color }"
    >{{ chunkText }}<text-annotation v-for="(r, index) in element.childs" :key="index" :text="text" :element="r" :labels="labels" @remove-label="$emit('remove-label', $event)"/><button class="delete is-small"
        style="top: 10px; left: -3px;"
        v-if="labels[element.label].text_color"
        @click="$emit('remove-label', element)"></button></span>
</template>

<script>
export default {
    name: 'text-annotation',
    props: {
        element: Object,
        labels: Object,
        text: String
    },
    methods: {
        removeLabel (element) {
            console.log('remove', element)
            this.$emit('remove-label', element)
        }
    },
    computed: {
        chunkText () {
            return this.text.slice(this.element.start_offset, this.element.childs && this.element.childs.length ? this.element.childs[0].start_offset : this.element.end_offset)
        }
    }
}
</script>