<template>
  <v-flex>
    <draggable v-model="cells">
      <cell v-for="c in cells" :key="c.key" :cell="c" />
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
  props: {
    contents: Object
  },
  computed: {
    cells() {
      let i = 0;
      return this.contents.cells.map(c => ({ ...c, key: i++ }));
    }
  }
};
</script>