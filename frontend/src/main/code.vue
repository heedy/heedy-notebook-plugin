<template>
  <v-hover v-slot:default="{ hover }">
    <div
      class="notebook-code-cell"
      :style="{'background': selected? '#a0a0a0' : hover? '#b0b0b0':'#c0c0c0'}"
    >
      <div style="flex: 1 1 auto">
        <codemirror
          :options="cmOptions"
          :value="code"
          @focus="selected=true"
          @blur="selected=false"
        />
      </div>
      <div style="flex-basis: content;">
        <div style="display: flex; flex-direction: column;align-items: center;">
          <!-- This div holds the cell toolbar-->
          <div v-if="!hover" style="height:24px;padding:2px; color: white; font-size: 12px;">1</div>
          <v-tooltip left v-else>
            <template v-slot:activator="{ on }">
              <v-btn
                fab
                text
                icon
                width="18"
                height="18"
                dark
                style="flex-basis:content;"
                v-on="on"
              >
                <v-icon size="10px">fas fa-play</v-icon>
              </v-btn>
            </template>
            <span>Run cell (shift+enter)</span>
          </v-tooltip>
          <v-menu bottom left>
            <template v-slot:activator="{ on }">
              <v-tooltip left>
                <template v-slot:activator="{ on:on2 }">
                  <v-btn
                    v-on="{...on,...on2}"
                    fab
                    text
                    icon
                    width="18"
                    height="18"
                    dark
                    style="flex-basis:content;"
                  >
                    <v-icon size="15px">more_vert</v-icon>
                  </v-btn>
                </template>
                <span>More</span>
              </v-tooltip>
            </template>
            <v-list dense>
              <v-list-item>
                <v-list-item-icon>
                  <v-icon size="20px">fab fa-markdown</v-icon>
                </v-list-item-icon>
                <v-list-item-content>Markdown</v-list-item-content>
              </v-list-item>
              <v-list-item>
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
  </v-hover>
</template>
<script>
export default {
  props: {
    code: String,
    readonly: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      cmOptions: {
        readOnly: this.readonly,
        mode: "python",
        theme: "neat",
        indentUnit: 4
      },
      selected: false
    };
  }
};
</script>
<style>
.notebook-code-cell .CodeMirror {
  height: auto;
  background: #efefef;
  min-height: 50px;
}
.notebook-code-cell {
  display: flex;
  flex-flow: row nowrap;
  align-items: flex-start;
  background: #a0a0a0;
  padding: 2px;
  border-radius: 3px;
  margin-top: 4px;
  box-shadow: 0 3px 1px -2px rgba(0, 0, 0, 0.2), 0 2px 2px 0 rgba(0, 0, 0, 0.14),
    0 1px 5px 0 rgba(0, 0, 0, 0.12);
}
</style>
