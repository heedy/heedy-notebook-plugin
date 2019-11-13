import Vue from "../../dist/vue.mjs";
import api from "../../api.mjs";

import uuidv4 from "uuid/v4";

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
                console.log(res);
                commit("setNotebook", {
                    id: q.id,
                    notebook: {
                        ...res.data.content,
                        cells: res.data.content.cells.map((c) => ({
                            ...c,
                            key: uuidv4()
                        }))
                    }
                })
            }
            if (q.hasOwnProperty("callback")) {
                q.callback();
            }
        }
    }
}