<template>
  <v-flex>
    <v-card>
      <notebook-header :source="source" :readonly="readonly" />
      <div class="text-center" v-if="loading" style="padding-top: 20px; padding-bottom: 40px;">
        <v-progress-circular :size="50" color="primary" indeterminate></v-progress-circular>
      </div>
      <notebook v-else v-model="contents" :readonly="readonly" @run="run" />
    </v-card>
  </v-flex>
</template>
<script>
import uuidv4 from "uuid/v4";
import moment from "../../dist/moment.mjs";
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
    loading: true,
    ws: null,
    session: uuidv4()
  }),
  computed: {
    contents: {
      get() {
        console.log(this.$store.state.notebooks.notebooks[this.source.id]);
        return this.$store.state.notebooks.notebooks[this.source.id] || [];
      },
      set(v) {
        if (this.ws == null) {
          this.startWS();
        }
        this.$store.commit("setNotebook", { id: this.source.id, notebook: v });
      }
    },
    readonly() {
      let s = this.source.access.split(" ");
      return !s.includes("*") && !s.includes("read");
    }
  },
  methods: {
    startWS() {
      if (this.ws !== null) {
        return;
      }
      let wsproto = "wss:";
      if (location.protocol == "http:") {
        wsproto = "ws:";
      }
      console.log("Starting kernel websocket ", this.source.id);
      this.ws = new WebSocket(
        `${wsproto}//${location.host}${location.pathname}api/heedy/v1/sources/${this.source.id}/kernel`
      );
      this.ws.onmessage = msg => {
        console.log(msg);
        let m = JSON.parse(msg.data);
        console.log(m["header"]["msg_type"]);
        let cellid = m["parent_header"]["msg_id"].split("_")[0];
        let cellindex = this.contents.cells.findIndex(v => v.key == cellid);
        if (cellindex < 0) {
          console.error("Couldn't find cell index", msg);
          return;
        }
        switch (m["header"]["msg_type"]) {
          case "execute_result":
            this.contents.cells[cellindex].outputs = [
              ...this.contents.cells[cellindex].outputs,
              { ...m["content"], output_type: "execute_result" }
            ];
            this.contents.cells[cellindex] = {
              ...this.contents.cells[cellindex]
            };
            this.contents = { ...this.contents }; // Force a redraw

            break;
          case "stream":
            this.contents.cells[cellindex].outputs = [
              ...this.contents.cells[cellindex].outputs,
              { ...m["content"], output_type: "stream" }
            ];
            this.contents.cells[cellindex] = {
              ...this.contents.cells[cellindex]
            };
            this.contents = { ...this.contents }; // Force a redraw

            break;
          case "error":
            this.contents.cells[cellindex].outputs = [
              ...this.contents.cells[cellindex].outputs,
              { text: m["content"]["traceback"].join(), output_type: "stream" }
            ];
            this.contents.cells[cellindex] = {
              ...this.contents.cells[cellindex]
            };
            this.contents = { ...this.contents }; // Force a redraw

            break;
        }
      };
    },
    run(i) {
      this.startWS();
      let hdr = {
        msg_id: this.contents.cells[i].key + "_" + uuidv4(),
        session: this.session,
        date: moment().toISOString(),
        msg_type: "execute_request"
      };
      let msg = JSON.stringify({
        header: hdr,
        parent_header: hdr,
        metadata: {},
        content: {
          code: this.contents.cells[i].source,
          silent: false
        }
      });
      console.log(msg);
      this.ws.send(msg);
      console.log("RUN", i);
    }
  },
  watch: {
    source(oldValue, newValue) {
      if (oldValue.id != newValue.id) {
        this.loading = true;
        if (this.ws != null) {
          console.log("Closing kernel ", this.source.id);
          this.ws.close();
          this.ws = null;
        }
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
  },
  beforeDestroy() {
    if (this.ws != null) {
      console.log("Closing kernel ", this.source.id);
      this.ws.close();
    }
  }
};
</script>