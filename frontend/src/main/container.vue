<template>
  <v-flex>
    <v-card>
      <notebook-header :source="source" />
      <div class="text-center" v-if="loading" style="padding-top: 20px; padding-bottom: 40px;">
        <v-progress-circular :size="50" color="primary" indeterminate></v-progress-circular>
      </div>
      <notebook v-else :contents="contents" />
    </v-card>
  </v-flex>
</template>
<script>
import NotebookHeader from "./header.vue";
import Notebook from "./notebook.vue";
export default {
  components: {
    NotebookHeader,
    Notebook
  },
  props: {
    source: Object
  },
  data: () => ({
    loading: true
  }),
  computed: {
    contents() {
      console.log(this.$store.state.notebooks.notebooks[this.source.id]);
      return this.$store.state.notebooks.notebooks[this.source.id] || [];
    }
  },
  watch: {
    source(oldValue, newValue) {
      if (oldValue.id != newValue.id) {
        this.loading = true;
        this.$store.dispatch("readNotebook", {
          id: newValue.id,
          callback: () => (this.loading = false)
        });
      }
    }
  },
  created() {
    this.$store.dispatch("readNotebook", {
      id: this.source.id,
      callback: () => (this.loading = false)
    });
  }
};
</script>