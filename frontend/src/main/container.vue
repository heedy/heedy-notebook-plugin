<template>
  <v-flex>
    <v-card>
      <notebook-header :source="source" />
      <notebook />
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
  }
};
</script>