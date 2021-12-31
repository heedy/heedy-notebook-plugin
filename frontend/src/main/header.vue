<template>
  <div>
    <v-toolbar flat>
      <v-toolbar-title>
        <h-icon :image="object.icon" :colorHash="object.id" :size="28" />
        {{ object.name }}
      </v-toolbar-title>
      <v-spacer></v-spacer>
      <h-menu-toolbar-items :toolbar="toolbar" :maxSize="toolbarSize" />
    </v-toolbar>
  </div>
</template>
<script>
import KernelStatusButton from "./kernel_status_button.vue";
export default {
  props: {
    object: Object,
    readonly: Boolean,
  },
  computed: {
    toolbar() {
      let menu = [
        {
          icon: "fas fa-download",
          text: "Download",
          click: () => this.download(),
          toolbar: true,
        },
      ];
      if (!this.readonly) {
        menu.push({
          icon: "fas fa-save",
          text: "Save",
          click: () =>
            this.$store.dispatch("saveNotebook", { id: this.object.id }),
          toolbar: true,
        });
        menu.push({
          icon: "play_arrow",
          text: "Run All",
          click: () =>
            this.$store.dispatch("runNotebook", { id: this.object.id }),
          toolbar: true,
        });
        menu.push({
          toolbar: true,
          toolbar_component: KernelStatusButton,
          menu_component: KernelStatusButton,
          toolbar_props: { objectId: this.object.id },
          menu_props: { objectId: this.object.id, isList: true },
        });
      }
      // Generate the menu items from the objectMenu
      return [
        ...menu,
        ...Object.values(
          this.$store.state.heedy.objectMenu.reduce(
            (o, m) => ({ ...o, ...m(this.object) }),
            {}
          )
        ),
      ];
    },
    toolbarSize() {
      if (this.$vuetify.breakpoint.xs) {
        return 1;
      }
      if (this.$vuetify.breakpoint.sm) {
        return 4;
      }
      if (this.$vuetify.breakpoint.md) {
        return 7;
      }
      return 10;
    },
  },
  methods: {
    download() {
      location.href =
        location.href.split("#")[0] +
        `api/objects/${this.object.id}/notebook.ipynb`;
    },
  },
};
</script>