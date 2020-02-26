<template>
  <div>
    <div v-if="collapsed">
      <v-tooltip bottom>
        <template #activator="{on}">
          <v-btn icon v-on="on" x-small @click="hide(false)">
            <v-icon>more_horiz</v-icon>
          </v-btn>
        </template>
        <span>Show Hidden</span>
      </v-tooltip>
    </div>
    <template v-else-if="cell.cell_type=='code'">
      <cell-code
        ref="code"
        v-model="source"
        :readonly="readonly"
        :count="execution_count"
        :modified="modified"
        @undo="$emit('undo')"
        @convert="convert"
        @delete="$emit('delete')"
        @addAbove="$emit('addAbove')"
        @addBelow="$emit('addBelow')"
        @hide="hide(true)"
        @run="run()"
      />
      <cell-output :output="cell.outputs" />
    </template>
    <template v-else-if="cell.cell_type=='markdown'">
      <div v-if="!editing || readonly" v-on:dblclick="editing=true">
        <execute-result :result="{'text/markdown': source}" />
      </div>

      <cell-code
        v-else
        ref="code"
        v-model="source"
        :readonly="readonly"
        lang="markdown"
        :modified="modified"
        @undo="$emit('undo')"
        @run="{editing=false;run()}"
        @convert="convert"
        @delete="$emit('delete')"
        @addAbove="$emit('addAbove')"
        @addBelow="$emit('addBelow')"
        @hide="hide(true)"
        :autofocus="true"
      />
    </template>
    <div v-else>Unknown cell type: {{ JSON.stringify(cell) }}</div>
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
  data: () => ({
    editing: false
  }),
  computed: {
    source: {
      get() {
        if (Array.isArray(this.cell.source)) {
          return this.cell.source.join("");
        }
        return this.cell.source;
      },
      set(v) {
        this.$emit("update", {
          ...this.cell,
          source: v
        });
      }
    },
    execution_count() {
      if (this.cell.metadata.execution_count !== undefined) {
        return this.cell.metadata.execution_count;
      }
      return 0;
    },
    collapsed() {
      if (this.cell.metadata.collapsed !== undefined) {
        return this.cell.metadata.collapsed;
      }
      return false;
    },
    modified() {
      return this.cell.modified !== undefined && this.cell.modified;
    }
  },
  methods: {
    convert(t) {
      let newcell = {
        cell_id: this.cell.cell_id,
        source: this.cell.source,
        cell_type: t,
        metadata: {}
      };
      if (t == "code") {
        newcell.outputs = [];
      } else if (t == "markdown") {
        this.editing = true;
      }
      console.log(newcell);
      this.$emit("update", newcell);
    },
    hide(v) {
      this.$emit("update", {
        ...this.cell,
        metadata: {
          ...this.cell.metadata,
          collapsed: v
        }
      });
    },
    run() {
      this.$emit("run", this.source);
    },
    focus() {
      if (this.collapsed) {
        this.hide(false);
      }
      setTimeout(() => this.$refs["code"].focus(), 0);
    }
  }
};
</script>
