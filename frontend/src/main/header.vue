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
          <v-btn icon v-on="on">
            <v-icon size="110%">fas fa-download</v-icon>
          </v-btn>
        </template>
        <span>Download</span>
      </v-tooltip>
      <div v-if="!readonly">
        <v-tooltip bottom>
          <template #activator="{on}">
            <v-btn icon v-on="on">
              <v-icon>replay</v-icon>
            </v-btn>
          </template>
          <span>Restart Kernel</span>
        </v-tooltip>
        <v-tooltip bottom>
          <template #activator="{on}">
            <v-btn icon v-on="on">
              <v-icon>play_arrow</v-icon>
            </v-btn>
          </template>
          <span>Run All</span>
        </v-tooltip>
        <v-tooltip bottom>
          <template #activator="{on}">
            <v-btn icon v-on="on">
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
  }
};
</script>