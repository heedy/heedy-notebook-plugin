import Vue from "../../dist/vue.mjs";
import api from "../../api.mjs";

export default {
    state: {
        notebooks: {}
    },
    mutations: {
        setNotebook(state, v) {
            Vue.set(state.notebooks, v.id, v.notebook);
        }
    },
    actions: {
        readNotebook: async function ({
            commit
        }, q) {
            let res = await api("GET", `api/heedy/v1/sources/${q.id}/contents`);
            if (res.response.ok) {
                commit("setNotebook", {
                    id: q.id,
                    notebook: res.data.content
                })
            }
            if (q.hasOwnProperty("callback")) {
                q.callback();
            }
        }
    }
}