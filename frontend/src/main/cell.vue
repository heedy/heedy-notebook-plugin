<template>
  <div>
    <template v-if="cell.cell_type=='code'">
      <cell-code :code="source" />
      <cell-output :output="cell.outputs" />
    </template>
    <template v-else-if="cell.cell_type=='markdown'">
      <execute-result :result="{'text/markdown': source}" />
    </template>
  </div>
</template>
<script>
import CellCode from "./code.vue";
import ExecuteResult from "./result.vue";
import CellOutput from "./output.vue";
export default {
  components: {
    CellCode,
    ExecuteResult,
    CellOutput
  },
  props: {
    cell: Object,
    readonly: {
      type: Boolean,
      default: false
    }
  },
  computed: {
    source() {
      if (Array.isArray(this.cell.source)) {
        return this.cell.source.join("");
      }
      return this.cell.source;
    }
  }
};
</script>
