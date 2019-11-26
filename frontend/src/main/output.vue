<template>
  <div class="notebook-cell-output">
    <div v-for="(c,i) in output" :key="i" style="padding-top: 5px;padding-bottom: 5px">
      <execute-result
        v-if="c.output_type=='execute_result' || c.output_type=='display_data'"
        :result="c.data"
      />
      <pre class="nberror" v-else-if="c.output_type=='error'" v-html="ansi(c.traceback)"></pre>
      <pre v-else-if="c.output_type=='stream'" v-html="ansi(c.text)" />
      <div v-else>{{ JSON.stringify(c)}}</div>
    </div>
  </div>
</template>
<script>
import ansi_up from "../../dist/ansi_up.mjs";
import ExecuteResult from "./result.vue";
export default {
  components: {
    ExecuteResult
  },
  data: () => ({
    cmOptions: {
      readOnly: true,
      mode: "text/plain",
      indentUnit: 4
    }
  }),
  props: {
    output: Array
  },
  methods: {
    ansi(txt) {
      if (Array.isArray(txt)) {
        txt = txt.join("\n");
      }
      return ansi_up.ansi_to_html(txt);
    }
  },
  watch: {
    output(nv, ov) {
      console.log(nv);
    }
  }
};
</script>
<style>
.notebook-cell-output .CodeMirror {
  height: auto;
}
.notebook-cell-output pre {
  padding: 10px;
  overflow: auto;
}
.notebook-cell-output .nberror {
  background-color: #ffcccb;
}
</style>