<template>
  <div class="notebook-result-cell" style="margin-top: 5px;padding: 5px;">
    <div
      v-if="result['text/html'] !== undefined"
      v-html="unArray(result['text/html'])"
      style="overflow-x: auto"
    ></div>
    <div v-else-if="result['text/markdown'] !== undefined" v-html="markdown"></div>
    <img v-else-if="imgv!==null" :src="imgv" />
    <pre v-else-if="Object.keys(result).length==1 && result['text/plain']!==undefined">{{ unArray(this.result["text/plain"]) }}</pre>
    <pre v-else>{{JSON.stringify(this.result) }}</pre>
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
      return md.render(this.unArray(this.result["text/markdown"]));
    },
    imgv() {
      let k = Object.keys(this.result).filter(x => x.startsWith("image/"));
      if (k.length == 0) {
        return null;
      }
      return `data:${k[0]};base64,${this.result[k[0]]}`;
    }
  },
  methods: {
    unArray(txt) {
      if (Array.isArray(txt)) {
        return txt.join("");
      }
      return txt;
    }
  }
};
</script>
<style >
.notebook-result-cell .CodeMirror {
  height: auto;
}

.notebook-result-cell img {
  max-width: 100%;
}

.notebook-result-cell table {
  border-collapse: collapse;
  border-color: #e8e8e8;
}

.notebook-result-cell td {
  padding: 8px;
}
.notebook-result-cell th {
  padding: 8px;
}

.notebook-result-cell tr:nth-child(even) {
  background-color: #f2f2f2;
}
</style>