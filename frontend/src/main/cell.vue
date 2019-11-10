<template>
  <div>
    <cell-code :code="code" />
    <cell-content :content="output" />
  </div>
</template>
<script>
import CellCode from "./code.vue";
import CellContent from "./content.vue";
export default {
  components: {
    CellCode,
    CellContent
  },
  props: {
    code: String,
    output: String,
    readonly: {
      type: Boolean,
      default: false
    }
  }
};
</script>
