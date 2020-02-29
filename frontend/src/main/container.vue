<template>
  <v-flex>
    <v-card>
      <notebook-header :object="object" :readonly="readonly" />
      <div class="text-center" v-if="loading" style="padding-top: 20px; padding-bottom: 40px;">
        <v-progress-circular :size="50" color="primary" indeterminate></v-progress-circular>
      </div>
      <notebook
        v-else
        :contents="contents"
        :readonly="readonly"
        @update="(c) => $store.commit('addNotebookUpdate',{id: object.id,data:c})"
        @undo="(c) => $store.commit('undoNotebookUpdates',{id: object.id,data:c})"
        @run="(c) => $store.dispatch('runNotebookCell',{id: object.id,data:c})"
        @save="$store.dispatch('saveNotebook', { id: object.id })"
      />
    </v-card>
  </v-flex>
</template>
<script>
import NotebookHeader from "./header.vue";
import Notebook from "./notebook.vue";

import updateNotebook from "./updateNotebook.js";

export default {
  components: {
    NotebookHeader,
    Notebook
  },
  props: {
    object: Object
  },
  data: () => ({
    loading: true
  }),
  computed: {
    contents() {
      console.log(this.$store.state.notebooks.notebooks[this.object.id]);
      if (
        this.$store.state.notebooks.notebooks[this.object.id] === undefined ||
        this.$store.state.notebooks.notebooks[this.object.id].notebook == null
      ) {
        return {};
      }
      let cur_nb = this.$store.state.notebooks.notebooks[this.object.id];
      let updated_nb = updateNotebook(cur_nb.notebook, cur_nb.updates, true);
      console.log("Updated", updated_nb);
      return updated_nb;
    },
    readonly() {
      let s = this.object.access.split(" ");
      return !s.includes("*") && !s.includes("write");
    }
  },
  methods: {
    run(i) {
      console.log(i);
    }
  },
  watch: {
    object(oldValue, newValue) {
      if (oldValue.id != newValue.id) {
        this.loading = true;
        this.$store.dispatch("readNotebook", {
          id: newValue.id,
          callback: () => (this.loading = false)
        });
        if (!this.readonly) {
          this.$store.dispatch("getNotebookStatus", {
            id: newValue.id,
            start: true
          });
        }
      }
    }
  },
  created() {
    this.$store.dispatch("readNotebook", {
      id: this.object.id,
      callback: () => (this.loading = false)
    });
    if (!this.readonly) {
      this.$store.dispatch("getNotebookStatus", {
        id: this.object.id,
        start: true
      });
    }
  },
  beforeDestroy() {}
};
</script>