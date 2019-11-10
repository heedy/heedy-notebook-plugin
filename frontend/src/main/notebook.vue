<template>
  <v-flex>
    <draggable v-model="codelist">
      <cell v-for="c in codelist" :key="c.key" :code="c.code" output="hey" />
    </draggable>
  </v-flex>
</template>
<script>
import Draggable from "../../dist/draggable.mjs";
import Cell from "./cell.vue";
export default {
  components: {
    Cell,
    Draggable
  },
  data: () => ({
    codelist: [{ key: "1", code: "2+2" }, { key: 2, code: "2+5" }]
  })
};
</script>