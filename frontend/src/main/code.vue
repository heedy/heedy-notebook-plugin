<template>
  <v-hover v-slot:default="{ hover }">
    <div
      class="notebook-code-cell"
      :style="{
        background: modified
          ? selected
            ? '#a0bfa0'
            : hover
            ? '#b0cab0'
            : '#c0cac0'
          : selected
          ? '#a0a0a0'
          : hover
          ? '#b0b0b0'
          : '#c0c0c0',
      }"
    >
      <div style="overflow-x: hidden">
        <codemirror
          :options="cmOptions"
          :value="value"
          ref="cm"
          @focus="selected = true"
          @blur="selected = false"
          @input="onInput"
        />
      </div>
      <div v-if="!readonly">
        <div
          style="
            display: flex;
            flex-direction: column;
            align-items: center;
            height: 100%;
          "
        >
          <!-- This div holds the cell toolbar-->
          <div style="flex-basis: content">
            <v-tooltip left v-if="lang == 'markdown'">
              <template v-slot:activator="{ on }">
                <v-btn
                  fab
                  text
                  icon
                  width="23"
                  height="23"
                  dark
                  v-on="on"
                  @click="$emit('run')"
                >
                  <v-icon size="10px">fab fa-markdown</v-icon>
                </v-btn>
              </template>
              <span>Show Markdown (shift+enter)</span>
            </v-tooltip>
            <div
              v-else-if="!hover && false"
              style="
                height: 23px;
                padding: 2px;
                padding-top: 4px;
                color: white;
                font-size: 12px;
              "
            >
              {{ count !== null ? count : "_" }}
            </div>
            <v-tooltip left v-else>
              <template v-slot:activator="{ on }">
                <v-btn
                  fab
                  text
                  icon
                  width="23"
                  height="23"
                  dark
                  v-on="on"
                  @click="$emit('run')"
                  style="padding-top: 0"
                >
                  <v-icon size="10px">fas fa-play</v-icon>
                </v-btn>
              </template>
              <span>Run cell (shift+enter)</span>
            </v-tooltip>
          </div>
          <div style="flex: 1; width: 24px" class="draghandle"></div>
          <div style="flex-basis: content">
            <v-menu bottom left>
              <template v-slot:activator="{ on }">
                <v-tooltip left>
                  <template v-slot:activator="{ on: on2 }">
                    <v-btn
                      v-on="{ ...on, ...on2 }"
                      fab
                      text
                      icon
                      width="23"
                      height="23"
                      dark
                    >
                      <v-icon size="15px">more_vert</v-icon>
                    </v-btn>
                  </template>
                  <span>More</span>
                </v-tooltip>
              </template>
              <v-list dense>
                <v-list-item
                  v-if="lang != 'markdown'"
                  @click="() => $emit('convert', 'markdown')"
                >
                  <v-list-item-icon>
                    <v-icon size="20px">fab fa-markdown</v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>Markdown</v-list-item-content>
                </v-list-item>
                <v-list-item v-else @click="() => $emit('convert', 'code')">
                  <v-list-item-icon>
                    <v-icon>code</v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>Code</v-list-item-content>
                </v-list-item>
                <v-list-item v-if="modified" @click="$emit('undo')">
                  <v-list-item-icon>
                    <v-icon size="20px">fas fa-undo</v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>Undo Changes</v-list-item-content>
                </v-list-item>
                <v-list-item @click="$emit('addAbove')">
                  <v-list-item-icon>
                    <v-icon size="20px">fas fa-arrow-circle-up</v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>Add cell above</v-list-item-content>
                </v-list-item>
                <v-list-item @click="$emit('addBelow')">
                  <v-list-item-icon>
                    <v-icon size="20px">fas fa-arrow-circle-down</v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>Add cell below</v-list-item-content>
                </v-list-item>
                <v-list-item @click="$emit('hide')">
                  <v-list-item-icon>
                    <v-icon size="20px">more_horiz</v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>Hide</v-list-item-content>
                </v-list-item>
                <v-list-item @click="$emit('delete')">
                  <v-list-item-icon>
                    <v-icon size="20px">fas fa-trash-alt</v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>Delete</v-list-item-content>
                </v-list-item>
              </v-list>
            </v-menu>
          </div>
        </div>
      </div>
    </div>
  </v-hover>
</template>
<script>
export default {
  model: {
    prop: "value",
    event: "input",
  },
  props: {
    value: String,
    modified: {
      type: Boolean,
      default: false,
    },
    lang: {
      type: String,
      default: "python",
    },
    readonly: {
      type: Boolean,
      default: false,
    },
    autofocus: {
      type: Boolean,
      default: false,
    },
    count: {
      type: Number,
      default: null,
    },
  },
  data: () => ({
    selected: false,
  }),
  computed: {
    cmOptions() {
      return {
        readOnly: this.readonly,
        mode: this.lang == "markdown" ? "gfm" : this.lang,
        theme: "neat",
        indentUnit: 4,
        extraKeys: {
          "Shift-Enter": () => this.$emit("run"),
          "Ctrl-Z": (cm) => {
            this.$emit("code-undo");
            cm.undo();
          },
          "Cmd-Z": (cm) => {
            this.$emit("code-undo");
            cm.undo();
          },
        },
        lineWrapping: false,
      };
    },
  },
  methods: {
    focus() {
      // BUG: for some reason, this causes codemirror to lock up, and refuse to type text
      this.$refs.cm.codemirror.focus();
    },
    onInput(v) {
      if (v != this.value) {
        this.$emit("input", v);
      }
    },
  },
};
</script>
<style>
.notebook-code-cell .CodeMirror {
  height: auto;
  background: #efefef;
  min-height: 60px;
}
.notebook-code-cell {
  /*display: flex;
  flex-flow: row nowrap;
  align-items: flex-start;*/
  display: grid;
  grid-template-columns: auto 25px;
  grid-gap: 0px;
  background: #a0a0a0;
  padding: 2px;
  border-radius: 3px;
  margin-top: 8px;
  margin-bottom: 4px;
  box-shadow: 0 3px 1px -2px rgba(0, 0, 0, 0.2), 0 2px 2px 0 rgba(0, 0, 0, 0.14),
    0 1px 5px 0 rgba(0, 0, 0, 0.12);
}
</style>
