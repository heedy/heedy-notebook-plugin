<template>
  <div>
    <v-toolbar flat>
      <v-toolbar-title>
        <h-icon :image="object.icon" :colorHash="object.id" :size="28" />
        {{ object.name }}
      </v-toolbar-title>
      <v-spacer></v-spacer>
      <v-tooltip bottom>
        <template #activator="{on}">
          <v-btn icon v-on="on" @click="download">
            <v-icon size="110%">fas fa-download</v-icon>
          </v-btn>
        </template>
        <span>Download</span>
      </v-tooltip>
      <div v-if="!readonly">
        <v-tooltip bottom>
          <template #activator="{on}">
            <v-btn icon v-on="on" @click="() => $store.dispatch('saveNotebook', { id: object.id })">
              <v-icon size="110%">fas fa-save</v-icon>
            </v-btn>
          </template>
          <span>Save</span>
        </v-tooltip>
        <v-tooltip bottom>
          <template #activator="{on}">
            <v-btn icon v-on="on" @click="() => $store.dispatch('runNotebook', { id: object.id })">
              <v-icon>play_arrow</v-icon>
            </v-btn>
          </template>
          <span>Run All</span>
        </v-tooltip>
        <v-tooltip bottom>
          <template #activator="{on}">
            <v-btn icon v-on="on" @click="status_button">
              <v-icon size="110%">{{ status_icon }}</v-icon>
            </v-btn>
          </template>
          <span>{{status_text}}</span>
        </v-tooltip>
        <v-tooltip bottom>
          <template #activator="{on}">
            <v-btn icon v-on="on" :to="`/objects/${object.id}/notebook/update`">
              <v-icon>edit</v-icon>
            </v-btn>
          </template>
          <span>Edit Object</span>
        </v-tooltip>
      </div>
    </v-toolbar>
  </div>
</template>
<script>
export default {
  props: {
    object: Object,
    readonly: Boolean
  },
  computed: {
    status_value() {
      if (
        this.$store.state.notebooks.notebooks[this.object.id] === undefined ||
        this.$store.state.notebooks.notebooks[this.object.id].notebook == null
      ) {
        return "unknown";
      }
      return this.$store.state.notebooks.notebooks[this.object.id].state;
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
    }
  },
  methods: {
    download() {
      location.href =
        location.href.split("#")[0] +
        `api/objects/${this.object.id}/notebook.ipynb`;
    },
    status_button() {
      let s = this.status_value;
      if (s == "busy")
        this.$store.dispatch("interruptNotebook", { id: this.object.id });
      else if (s == "idle")
        this.$store.dispatch("stopNotebook", { id: this.object.id });
      else if (s == "off")
        this.$store.dispatch("getNotebookStatus", {
          id: this.object.id,
          start: true
        });
    }
  }
};
</script>