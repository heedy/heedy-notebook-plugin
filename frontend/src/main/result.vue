<template>
  <div class="notebook-result-cell" style="margin-top: 5px;padding: 5px;">
    <div v-if="result['text/html'] !== undefined" v-html="result['text/html'] "></div>
    <div v-else-if="result['text/markdown'] !== undefined" v-html="markdown"></div>
    <img
      v-else-if="result['image/png']!==undefined"
      :src="`data:image/png;base64,${result['image/png']}`"
    />
    <codemirror
      v-else-if="Object.keys(result).length==1 && result['text/plain']!==undefined"
      :options="cmOptions"
      :value="result['text/plain']"
    />
    <div v-else>{{JSON.stringify(result) }}</div>
  </div>
</template>
<script>
import { md } from "../../dist/markdown-it.mjs";
export default {
  props: {
    result: Object
  },
  data: () => ({
    cmOptions: {
      readOnly: true,
      mode: "text/plain",
      indentUnit: 4
    }
  }),
  computed: {
    markdown() {
      return md.render(this.result["text/markdown"]);
    }
  }
};
</script>
<style >
.notebook-result-cell .CodeMirror {
  height: auto;
}
</style>