<template>
  <h-card-page title="Create a new Notebook" :alert="alert">
    <v-container fluid grid-list-md>
      <v-layout row>
        <v-flex sm5 md4 xs12>
          <h-icon-editor ref="iconEditor" image="code"></h-icon-editor>
        </v-flex>
        <v-flex sm7 md8 xs12>
          <v-container>
            <v-text-field label="Name" placeholder="My Notebook" v-model="name"></v-text-field>
            <v-text-field
              label="Description"
              placeholder="This notebook does analysis"
              v-model="description"
            ></v-text-field>
            <v-radio-group v-model="notebook" style="margin-top:-10px;margin-bottom: -50px;">
              <v-radio value="blank" label="Create Blank Notebook"></v-radio>
              <v-radio value="import" label="Import from URL"></v-radio>
              <v-radio value="upload" label="Upload from File"></v-radio>
            </v-radio-group>
          </v-container>
        </v-flex>
      </v-layout>
    </v-container>
    <v-card-actions>
      <v-spacer></v-spacer>
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
    name: "",
    notebook: "blank",
    upload_url: ""
  }),
  methods: {
    create: async function() {
      if (this.loading) return;

      this.loading = true;

      if (this.name == "") {
        this.alert = "Must fill in notebook name";
        this.loading = false;
        return;
      }

      let toCreate = {
        name: this.name,
        type: "notebook"
      };
      toCreate.description = this.description;
      toCreate.icon = this.$refs.iconEditor.getImage();

      let result = await this.$app.api(
        "POST",
        `api/heedy/v1/sources`,
        toCreate
      );

      if (!result.response.ok) {
        this.alert = result.data.error_description;
        this.loading = false;
        return;
      }
      // The result comes without the icon, let's set it correctly
      result.data.icon = toCreate.icon;

      this.$store.commit("setSource", result.data);
      this.loading = false;
      this.$router.replace({ path: `/sources/${result.data.id}` });
    }
  }
};
</script>