<template>
  <h-card-page title="Create a new Notebook" :alert="alert">
    <v-container fluid grid-list-md>
      <v-layout row>
        <v-flex sm5 md4 xs12>
          <h-icon-editor ref="iconEditor" image="code"></h-icon-editor>
        </v-flex>
        <v-flex sm7 md8 xs12>
          <v-container>
            <v-text-field
              label="Name"
              placeholder="My Notebook"
              v-model="name"
              autofocus
            ></v-text-field>
            <v-text-field
              label="Description"
              placeholder="This notebook does analysis"
              v-model="description"
            ></v-text-field>
            <h-tag-editor v-model="tags" />
            <v-radio-group
              v-model="notebook"
              style="margin-top: -10px; margin-bottom: -50px"
            >
              <v-radio value="blank" label="Blank Notebook"></v-radio>
              <v-radio value="upload" label="Upload from File"></v-radio>
            </v-radio-group>
            <div v-if="notebook == 'upload'" style="margin-top: 25px">
              <v-file-input
                v-model="file"
                v-if="!uploading"
                show-size
                label="Jupyter Notebook (.ipynb)"
              ></v-file-input>
              <v-progress-linear
                v-else
                :value="uploadPercent"
              ></v-progress-linear>
              <v-btn v-if="uploading" dark @click="cancelUpload">Cancel</v-btn>
            </div>
          </v-container>
        </v-flex>
      </v-layout>
    </v-container>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn text @click="$router.go(-1)">Cancel</v-btn>
      <v-btn dark color="blue" @click="create" :loading="loading">Create</v-btn>
    </v-card-actions>
  </h-card-page>
</template>
<script>
export default {
  data: () => ({
    alert: "",
    loading: false,
    description: "",
    tags: "",
    name: "",
    notebook: "blank",
    upload_url: "",
    uploading: false,
    uploadPercent: 0,
    file: null,
    xhr: null,
  }),
  methods: {
    create: async function () {
      if (this.loading) return;

      this.loading = true;

      if (this.name == "") {
        this.alert = "Must fill in notebook name";
        this.loading = false;
        return;
      }

      let toCreate = {
        name: this.name,
        type: "notebook",
        description: this.description,
        tags: this.tags,
        icon: this.$refs.iconEditor.getImage(),
      };

      let result = await this.$frontend.rest("POST", `api/objects`, toCreate);

      if (!result.response.ok) {
        this.alert = result.data.error_description;
        this.loading = false;
        return;
      }
      // The result comes without the icon, let's set it correctly
      result.data.icon = toCreate.icon;
      this.$store.commit("setObject", result.data);

      // Finish if we are not uploading
      if (this.notebook != "upload") {
        this.loading = false;
        this.$router.replace({ path: `/objects/${result.data.id}` });
        return;
      }

      this.uploading = true;
      let form = new FormData();
      form.append("notebook", this.file);

      var xhr = new XMLHttpRequest();
      xhr.upload.addEventListener(
        "progress",
        (evt) => {
          if (evt.lengthComputable) {
            this.uploadPercent = Math.floor((100 * evt.loaded) / evt.total);
          }
        },
        false
      );
      let endRequest = async () => {
        await this.$frontend.rest("DELETE", `api/objects/${result.data.id}`);
        this.file = null;
        this.uploading = false;
        this.loading = false;
        this.xhr = null;
      };
      xhr.addEventListener("load", (evt) => {
        if (evt.target.status != 200) {
          try {
            this.alert =
              "Upload failed: " +
              JSON.parse(evt.target.response).error_description;
          } catch {
            this.alert = "Upload failed";
          }
          endRequest();
          return;
        }
        // Success, go to the notebook
        this.loading = false;
        this.$router.replace({ path: `/objects/${result.data.id}` });
      });
      xhr.addEventListener("error", (evt) => {
        console.error("Upload failed:", evt);
        endRequest();
        this.alert = "Upload failed";
      });
      xhr.addEventListener("abort", (evt) => {
        console.warn("Upload aborted", evt);
        endRequest();
      });
      xhr.open("POST", `api/objects/${result.data.id}/notebook.ipynb`);
      xhr.send(form);
      this.xhr = xhr;
    },
    cancelUpload() {
      if (this.xhr != null) {
        this.xhr.abort();
      } else {
        this.uploading = false;
      }
    },
  },
};
</script>