<template>
  <v-flex>
    <draggable :value="cells" :disabled="readonly" @end="onMove">
      <cell
        v-for="(c,i) in cells"
        :ref="c.cell_id"
        :key="c.cell_id"
        :cell="c"
        @undo="() => $emit('undo',{cell_id: c.cell_id})"
        @update="(v) => $emit('update',v)"
        @delete="() => $emit('update',{cell_id: c.cell_id,delete: true})"
        @addAbove="() => $emit('update',{cell_id: mkid(),cell_index: c.cell_index})"
        @addBelow="() => $emit('update',{cell_id: mkid(),cell_index: c.cell_index+1})"
        @run="(v)=> run(c.cell_id,v,i)"
        @save="$emit('save')"
        :readonly="readonly"
      />
    </draggable>
  </v-flex>
</template>
<script>
import Draggable from "../../dist/draggable.mjs";
import Cell from "./cell.vue";
import uuidv4 from "../../dist/uuid.mjs";
export default {
  components: {
    Cell,
    Draggable
  },
  props: {
    contents: Object,
    readonly: Boolean
  },
  computed: {
    cells() {
      let c = Object.values(this.contents);
      c.sort((a, b) => a["cell_index"] - b["cell_index"]);
      return c;
    }
  },
  watch: {
    contents(nv, ov) {
      // Make sure that there is at least the initial starting cell
      if (Object.keys(nv).length == 0 && !this.readonly) {
        this.$emit("update", { cell_id: uuidv4() });
      }
    }
  },
  methods: {
    mkid() {
      return uuidv4();
    },
    onMove(evt) {
      console.log("Cell drag-drop", evt);
      this.$emit("update", {
        cell_id: this.cells[evt.oldIndex].cell_id,
        cell_index: evt.newIndex
      });
    },
    run(cell_id, source, i) {
      this.$emit("run", {
        cell_id: cell_id,
        source: source
      });
      // Find the next element to focus
      for (let j = i + 1; j < this.cells.length; j++) {
        if (this.cells[j].cell_type == "code") {
          this.$refs[this.cells[j].cell_id][0].focus();
          return;
        }
      }
      // Add a cell to the end, and focus it
      this.$emit("update", { cell_id: uuidv4() });
      setTimeout(
        () => this.$refs[this.cells[this.cells.length - 1].cell_id][0].focus(),
        100
      );
    }
  },
  created() {
    if (this.cells.length == 0 && !this.readonly) {
      this.$emit("update", { cell_id: uuidv4() });
    }
  }
};
</script>