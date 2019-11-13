<template>
  <div class="notebook-cell-output">
    <div v-for="(c,i) in output" :key="i" style="padding-top: 5px;padding-bottom: 5px">
      <execute-result
        v-if="c.output_type=='execute_result' || c.output_type=='display_data'"
        :result="c.data"
      />
      <codemirror v-else-if="c.output_type=='stream'" :options="cmOptions" :value="c.text" />
      <div v-else>{{ JSON.stringify(c)}}</div>
    </div>
  </div>
</template>
<script>
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
</style>