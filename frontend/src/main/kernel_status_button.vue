<template>
  <v-tooltip bottom v-if="!isList">
    <template #activator="{ on }">
      <v-btn icon v-on="on" @click="status_button">
        <v-icon>{{ status_icon }}</v-icon>
      </v-btn>
    </template>
    <span>{{ status_text }}</span>
  </v-tooltip>
  <v-list-item v-else @click="status_button">
    <v-list-item-icon>
      <v-icon>{{ status_icon }}</v-icon>
    </v-list-item-icon>
    <v-list-item-content>
      <v-list-item-title>{{ status_text }}</v-list-item-title>
    </v-list-item-content>
  </v-list-item>
</template>
<script>
export default {
  props: {
    isList: {
      type: Boolean,
      default: false,
    },
    objectId: {
      type: String,
      default: "",
    },
  },
  computed: {
    status_value() {
      if (
        this.$store.state.notebooks.notebooks[this.objectId] === undefined ||
        this.$store.state.notebooks.notebooks[this.objectId].notebook == null
      ) {
        return "unknown";
      }
      return this.$store.state.notebooks.notebooks[this.objectId].state;
    },
    status_icon() {
      let s = this.status_value;
      if (s == "busy") return "fas fa-hourglass-start";
      if (s == "idle") return "fas fa-check-square";
      if (s == "off") return "fas fa-play-circle";
      return "fas fa-hourglass-start";
    },
    status_text() {
      let s = this.status_value;
      if (s == "busy") return "Kernel Busy (Click to Interrupt)";
      if (s == "idle") return "Kernel Idle (Click to Stop)";
      if (s == "off") return "Kernel Off (Click to Start)";
      if (s == "starting") return "Kernel Starting...";
      return "Waiting for Kernel Status...";
    },
  },
  methods: {
    status_button() {
      let s = this.status_value;
      if (s == "busy")
        this.$store.dispatch("interruptNotebook", { id: this.objectId });
      else if (s == "idle")
        this.$store.dispatch("stopNotebook", { id: this.objectId });
      else if (s == "off")
        this.$store.dispatch("getNotebookStatus", {
          id: this.objectId,
          start: true,
        });
    },
  },
};
</script>
