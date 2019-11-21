<template>
  <v-flex>
    <draggable v-model="cells" :disabled="readonly">
      <cell
        v-for="(c,i) in contents.cells"
        :ref="c.key"
        :key="c.key"
        :cell="c"
        @update="(v) => {contents.cells[i]=v;update();}"
        @delete="() => {contents.cells.splice(i,1);update()}"
        @addAbove="() => addCell(i)"
        @addBelow="() => addCell(i+1)"
        @run="(v)=> run(i)"
        :readonly="readonly"
      />
    </draggable>
  </v-flex>
</template>
<script>
import Draggable from "../../dist/draggable.mjs";
import Cell from "./cell.vue";
import uuidv4 from "uuid/v4";
export default {
  model: {
    prop: "contents",
    event: "update"
  },
  components: {
    Cell,
    Draggable
  },
  props: {
    contents: Object,
    readonly: Boolean
  },
  computed: {
    cells: {
      get() {
        return this.contents.cells;
      },
      set(v) {
        this.$emit("update", { ...this.contents, cells: v });
      }
    }
  },
  watch: {
    contents(nv, ov) {
      console.log("CONTENT REDRAW");
      // Make sure that there is at least the initial starting cell
      if (nv.cells.length == 0 && !this.readonly) {
        this.addCell(nv.cells.length);
      }
    }
  },
  created() {
    if (this.cells.length == 0 && !this.readonly) {
      this.addCell(this.cells.length);
    }
  },
  methods: {
    update() {
      this.$emit("update", { ...this.contents });
    },
    addCell(i) {
      this.contents.cells.splice(i, 0, {
        key: uuidv4(),
        object: "",
        cell_type: "code",
        metadata: {},
        outputs: [],
        execution_count: null
      });
      this.$emit("update", { ...this.contents });
    },
    run(i) {
      // Dispatch the run event
      if (this.cells[i].cell_type == "code") {
        this.$emit("run", i);
      }

      // Clear cell contents
      this.cells[i] = { ...this.cells[i], outputs: [] };

      // Find the next element to focus
      for (let j = i + 1; j < this.cells.length; j++) {
        if (this.cells[j].cell_type == "code") {
          this.$refs[this.cells[j].key][0].focus();

          // Clear the contents of the cell needs to call an update
          this.update();
          return;
        }
      }
      // Add a cell to the end, and focus it
      this.addCell(this.cells.length);
      setTimeout(
        () => this.$refs[this.cells[this.cells.length - 1].key][0].focus(),
        100
      );
    }
  }
};
</script>