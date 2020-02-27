<template>
  <h-card-page :title="'Update ' + object.name" :alert="alert">
    <v-container fluid grid-list-md>
      <v-layout row>
        <v-flex sm5 md4 xs12>
          <h-icon-editor
            ref="iconEditor"
            :image="object.icon"
            :colorHash="object.id"
            defaultIcon="code"
          ></h-icon-editor>
        </v-flex>
        <v-flex sm7 md8 xs12>
          <v-container>
            <v-text-field label="Name" placeholder="My Notebook" v-model="name"></v-text-field>
            <v-text-field
              label="Description"
              placeholder="This notebook does analysis"
              v-model="description"
            ></v-text-field>
            <h-tag-editor v-model="tags" />
          </v-container>
        </v-flex>
      </v-layout>
    </v-container>
    <v-card-actions>
      <v-btn dark color="red" @click="del" :loading="loading">Delete</v-btn>
      <v-spacer></v-spacer>
      <v-btn dark color="blue" @click="update" :loading="loading">Update</v-btn>
    </v-card-actions>
  </h-card-page>
</template>
<script>
export default {
  props: {
    object: Object
  },
  data: () => ({
    alert: "",
    modified: {},
    loading: false
  }),
  methods: {
    update: async function() {
      if (this.loading) return;

      this.loading = true;
      this.alert = "";

      if (this.$refs.iconEditor.hasImage()) {
        // We are in the image picker, and an image was chosen
        this.modified.icon = this.$refs.iconEditor.getImage();
      }

      let mod = this.modified;
      if (Object.keys(this.modified).length > 0) {
        console.log("UPDATING", mod);
        let result = await this.$app.api(
          "PATCH",
          `api/objects/${this.object.id}`,
          mod
        );

        if (!result.response.ok) {
          this.alert = result.data.error_description;
          this.loading = false;
          return;
        }
        this.$store.dispatch("readObject", {
          id: this.object.id
        });
      }

      this.loading = false;
      this.$router.go(-1);
    },
    del: async function() {
      let s = this.object;
      if (
        confirm(
          `Are you sure you want to delete '${this.object.name}'? This deletes all associated data.`
        )
      ) {
        let res = await this.$app.api(
          "DELETE",
          `/api/objects/${this.object.id}`
        );
        if (!res.response.ok) {
          this.alert = res.data.error_description;
        } else {
          this.alert = "";
          if (s.app != null) {
            this.$router.push(`/apps/${s.app}`);
          } else {
            this.$router.push(`/users/${s.owner}`);
          }
        }
      }
    }
  },
  computed: {
    description: {
      get() {
        if (this.modified.description !== undefined) {
          return this.modified.description;
        }
        return this.object.description;
      },
      set(v) {
        this.$app.vue.set(this.modified, "description", v);
      }
    },
    name: {
      get() {
        if (this.modified.name !== undefined) {
          return this.modified.name;
        }
        return this.object.name;
      },
      set(v) {
        this.$app.vue.set(this.modified, "name", v);
      }
    },
    tags: {
      get() {
        if (this.modified.tags !== undefined) {
          return this.modified.tags;
        }
        return this.object.tags;
      },
      set(v) {
        this.$app.vue.set(this.modified, "tags", v);
      }
    }
  }
};
</script>
