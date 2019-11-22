<template>
  <v-flex>
    <v-card>
      <notebook-header :object="object" :readonly="readonly" />
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
    object: Object
  },
  data: () => ({
    loading: true,
    ws: null,
    session: uuidv4()
  }),
  computed: {
    contents: {
      get() {
        console.log(this.$store.state.notebooks.notebooks[this.object.id]);
        return this.$store.state.notebooks.notebooks[this.object.id] || [];
      },
      set(v) {
        if (this.ws == null) {
          this.startWS();
        }
        this.$store.commit("setNotebook", { id: this.object.id, notebook: v });
      }
    },
    readonly() {
      let s = this.object.access.split(" ");
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
      console.log("Starting kernel websocket ", this.object.id);
      this.ws = new WebSocket(
        `${wsproto}//${location.host}${location.pathname}api/heedy/v1/objects/${this.object.id}/kernel`
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
        let applycontents = () => {
          if (m["content"]["execution_count"] !== undefined) {
            this.contents.cells[cellindex].execution_count =
              m["content"]["execution_count"];
          }
          this.contents.cells[cellindex].outputs = [
            ...this.contents.cells[cellindex].outputs,
            { ...m["content"], output_type: m["header"]["msg_type"] }
          ];
          this.contents.cells[cellindex] = {
            ...this.contents.cells[cellindex]
          };
          this.contents = { ...this.contents }; // Force a redraw
        };
        switch (m["header"]["msg_type"]) {
          case "execute_result":
            applycontents();
            break;
          case "display_data":
            applycontents();
            break;
          case "stream":
            applycontents();
            break;
          case "error":
            applycontents();
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
        metadata: {
          cellId: this.contents.cells[i].key,
          deletedCells: [],
          recordTiming: false
        },
        channel: "shell",
        buffers: [],
        content: {
          code: this.contents.cells[i].source,
          silent: false,
          allow_stdin: false,
          stop_on_error: true,
          store_history: true
        }
      });
      console.log(msg);
      this.ws.send(msg);
      console.log("RUN", i);
    }
  },
  watch: {
    object(oldValue, newValue) {
      if (oldValue.id != newValue.id) {
        this.loading = true;
        if (this.ws != null) {
          console.log("Closing kernel ", this.object.id);
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
      id: this.object.id,
      callback: () => (this.loading = false)
    });
  },
  beforeDestroy() {
    if (this.ws != null) {
      console.log("Closing kernel ", this.object.id);
      this.ws.close();
    }
  }
};
</script>