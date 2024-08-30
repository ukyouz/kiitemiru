async function restful_get(endpoint) {
    const request = await fetch(endpoint, {
        credentials: "same-origin",
        headers: {
            "X-CSRF-Token": document.head.querySelector("[name~=csrf_token][content]").content,
        },
    });
    const response = await request.json();
    console.log(response)
    return response;
}

var player;

const AUTOJUMP_THRESHOLDE_SEC = 7;

const urlQuery = new URLSearchParams(window.location.search);

document.addEventListener('alpine:init', function () {
    Alpine.data('mainjs', () => ({
        term: urlQuery.get('q') ? decodeURI(urlQuery.get('q')) : '',
        videos: [
            {
                info: {
                    id: "XYxKhjPh138",
                    title: "loading ...",
                    thumbnail: "/static/load-loading.gif",
                    published_at: "2024-01-01T00:00:00Z",
                    channel: "just a moment ...",
                },
                captions: [
                    { timestamp: 10.0, duration: 1, caption: "loading..." },
                    // { timestamp: 12.4, duration: 1, caption: "うん ち 画 クイズ 収録 は 半年ぶり に なり ます" },
                    // { timestamp: 35.5, duration: 1, caption: "クイズ と は 何 です か あ あ そう か そはい あの" },
                    // { timestamp: 37.1, duration: 1, caption: "我々 よく この クイズ を ね ゆり 言語 ワク" },
                    // { timestamp: 39.2, duration: 1, caption: "ラジオ で やっ てる ん です が ただ の クイズ で" },
                ],
            },
        ],
        is_ngram: urlQuery.get('options') ? urlQuery.get('options').includes("ngram") : false,
        is_intense: urlQuery.get('options') ? urlQuery.get('options').includes("intense") : false,
        is_random: urlQuery.get('options') ? urlQuery.get('options').includes("random") : false,
        is_autojump: true,

        curr_page: 1,
        total_page: -1,
        page_offset: -1,
        total_found: 0,

        forward_sec: 5,
        status: urlQuery.get('q') ? "loading" : "init", // init, loading, loaded, not_found
        current_pos: 0,
        current_cap: 0,
        wait_for_next_timeout: null,

        get captions() {
            return this.videos[this.current_pos]?.captions || [];
        },

        get vinfo() {
            return this.videos[this.current_pos]?.info || {};
        },

        get paginations() {
            const margin = 2;
            const visible = margin * 2 + 1;

            if (this.total_page <= visible) {
                return Array.from({ length: this.total_page }, (_, i) => i + 1);
            }

            if (this.curr_page - 1 <= margin) {
                // left edge
                let pages = Array.from({ length: visible }, (_, i) => i + 1);
                return [...pages, -1]
            } else if (this.curr_page >= this.total_page - margin) {
                // right edge
                let pages = Array.from({ length: visible }, (_, i) => this.total_page - visible + i + 1);
                return [1, -1, ...pages]
            } else {
                // middle
                let pages = Array.from({ length: visible }, (_, i) => this.curr_page - margin + i + 1);
                return [1, -1, ...pages, -1]
            }
        },

        stop_autoplay: function () {
            this.is_autojump = false;
        },

        select_video: function (index, reload = false) {
            if (!reload && index == this.current_pos) {
                return;
            }
            if (index >= this.videos.length) {
                if (this.videos.length) {
                    index = 0;
                } else {
                    return;
                }
            }
            if (this.wait_for_next_timeout) {
                clearTimeout(this.wait_for_next_timeout);
                this.wait_for_next_timeout = null;
            }
            this.status = "loaded";
            this.current_pos = index;
            this.current_cap = 0;
            //console.log(1, player)
            if (player) {
                first_ts = this.captions[this.current_cap].timestamp;
                player.loadVideoById(this.vinfo.id, first_ts);
            }
            setTimeout(() => {
                this.scrollToCaption();
            }, 0);
        },

        search_next_cap: function (time) {
            for (let i = 0; i < this.captions.length; i++) {
                let ts = this.captions[i].timestamp;
                if (this.captions[i].timestamp > time) {
                    return i;
                }
            }
            return -1;
        },

        invalidate_caption: function (vid_ts) {
            // when video is seeked, invalidate current selected caption
            for (let i = 0; i < this.captions.length; i++) {
                let ts = this.captions[i].timestamp;
                let length = this.captions[i].duration;
                if (ts <= vid_ts && vid_ts <= ts + length) {
                    return;
                }
            }
            this.current_cap = -1;
        },

        clear_timeout: function () {
            if (this.wait_for_next_timeout) {
                clearTimeout(this.wait_for_next_timeout);
                this.wait_for_next_timeout = null;
            }
        },

        set_timeout: function (cb, sec) {
            this.wait_for_next_timeout = setTimeout(cb, sec * 1000);
        },

        on_autojump_changed: function () {
            if (this.is_autojump && player && this.videos.length) {
                this.youtube_ticked(player.getCurrentTime(), player.getPlayerState());
            }
        },

        on_intense_changed: function () {
            if (!this.is_random) {
                this.is_random = true;
            }
        },

        youtube_ticked: function (vid_ts, status) {
            this.clear_timeout();
            if (status == YT.PlayerState.ENDED) {
                if (this.is_autojump) {
                    this.current_cap = -1;
                    this.select_video(this.current_pos + 1);
                    return;
                }
            }
            else if (status != YT.PlayerState.PLAYING) {
                return
            }
            this.invalidate_caption(vid_ts);

            let curr_cap = this.current_cap;
            const tune_back = vid_ts < this.captions[curr_cap].timestamp;
            if (curr_cap == -1 || tune_back) {
                /* no prev selected caption, just go to next one */
                let next_cap = this.search_next_cap(vid_ts);
                if (next_cap == -1) {
                    return;
                }
                let next_ts = this.captions[next_cap].timestamp;
                if ((this.is_autojump && (next_ts - vid_ts) > AUTOJUMP_THRESHOLDE_SEC) || tune_back) {
                    // only jump if the next caption is far away enough (> AUTOJUMP_THRESHOLDE_SEC sec)
                    // or go back manually
                    this.select_caption(next_cap);
                    return;
                }
                this.set_timeout(() => {
                    this.current_cap = next_cap;
                    this.youtube_ticked(player.getCurrentTime(), status);
                }, next_ts - vid_ts);
                return;
            }
            let curr_duration = this.captions[curr_cap].duration;
            let next_cap = curr_cap + 1;
            if (next_cap >= this.captions.length) {
                /* next one is the last one, just clear out current one */
                this.set_timeout(() => {
                    this.current_cap = -1;
                    if (this.is_autojump) {
                        this.select_video(this.current_pos + 1);
                    }
                }, curr_duration);
                return;
            }
            /* move from current to next one */
            let next_ts = this.captions[next_cap].timestamp;
            if (next_ts <= vid_ts) {
                // when next caption is still too early
                // just jump farward to the closest one
                next_cap = this.search_next_cap(vid_ts);
                this.current_cap = next_cap;
                this.youtube_ticked(player.getCurrentTime(), status);
            } else if (next_ts - vid_ts <= curr_duration) {
                // go to next caption without waiting
                this.set_timeout(() => {
                    this.current_cap = next_cap;
                    this.youtube_ticked(player.getCurrentTime(), status);
                }, next_ts - vid_ts);
                console.log("next caption", (next_ts - vid_ts));
            } else {
                // next caption is too far away
                this.set_timeout(() => {
                    this.current_cap = -1;
                    if (this.is_autojump && (next_ts - vid_ts - curr_duration) > AUTOJUMP_THRESHOLDE_SEC) {
                        // only jump if the next caption is far away enough (> AUTOJUMP_THRESHOLDE_SEC sec)
                        this.select_caption(next_cap);
                    } else {
                        this.youtube_ticked(player.getCurrentTime(), status);
                    }
                }, curr_duration);
                console.log("waiting for next caption", curr_duration, (next_ts - vid_ts));
            }
        },

        select_caption: function (index) {
            this.clear_timeout();
            this.current_cap = index;
            this.seek(this.captions[index].timestamp);
        },

        get search_option_query() {
            let options = [];
            if (this.is_ngram) {
                options.push("ngram");
            }
            if (this.is_intense) {
                options.push("intense");
            }
            if (this.is_random) {
                options.push("random");
            }
            return options.join("|");
        },

        search_from_input: async function (e) {
            urlQuery.delete('offset');

            let current_url = window.location.pathname.split('?')[0];
            let url_opts = urlQuery.get('options') || "";

            if (current_url != "/") {
                window.location = "/?q=" + this.term;
            } else if (urlQuery.get('q') != this.term || url_opts != this.search_option_query) {
                urlQuery.set('q', this.term);
                if (this.search_option_query) {
                    urlQuery.set('options', this.search_option_query);
                } else {
                    urlQuery.delete('options');
                }
                window.location.search = urlQuery.toString();
            } else {
                this.search_token(e);
            }
        },

        search_token: async function (e) {
            if (e.isComposing) {
                // ここは Japanese IME 変換確認
                return;
            }
            if (this.term == "") {
                return;
            }
            // document.querySelectorAll("input[type=search]").forEach((input) => {
            //     input.blur();
            // });

            //console.log(this.term);
            let res = [];

            if (this.is_ngram && this.term.length == 1) {
                q = urlQuery.toString().replace("ngram", "");
                res = await restful_get(`/query/search/?${q}`);
            } else {
                res = await restful_get(`/query/search/?${urlQuery.toString()}`);
            }
            curr_pos = res["summary"]["curr_offset"];
            next_pos = res["summary"]["next_offset"];
            step = next_pos - curr_pos;
            total_found = res["summary"]["total_found"];
            this.curr_page = Math.floor(curr_pos / step) + 1;
            this.total_page = Math.ceil(total_found / step);
            this.page_offset = step;
            this.total_found = res["summary"]["total_found"];
            this.videos = res["items"];
            if (this.videos.length == 0) {
                this.status = "not_found";
            } else {
                this.select_video(0, true);
            }
        },

        on_showall_req: async function () {
            this.clear_timeout();
            res = await restful_get(`/query-video/captions/${this.vinfo.id}`)
            current_ts = this.captions[this.current_cap].timestamp;
            this.videos[this.current_pos].info.all_loaded = true;
            this.videos[this.current_pos].captions = res["items"];
            for (let i = 0; i < res["items"].length; i++) {
                if (res["items"][i].timestamp >= current_ts) {
                    this.current_cap = i;
                    break;
                }
            }
        },

        scrollToCaption: function () {
            current_ts = this.captions[this.current_cap].timestamp;
            let li = document.querySelector(`[data-ts='${current_ts}']`);
            let pos = this.current_cap == 0 ? "end" : "center";
            if (li) {
                li.scrollIntoView({ block: pos });
            }
        },

        goto_page: async function (page) {
            if (this.curr_page == page || page < 1 || page > this.total_page) {
                return;
            }
            if (page == 1) {
                urlQuery.delete('offset');
            } else {
                urlQuery.set('offset', (page - 1) * this.page_offset);
            }
            window.location.search = urlQuery.toString();
        },


        fmttime: function (seconds) {
            var sec = Math.floor(seconds);
            var min = Math.floor(sec / 60);
            var hour = Math.floor(min / 60);
            sec = sec % 60;
            min = min % 60;
            if (hour > 0) {
                return hour + ":" + min.toString().padStart(2, '0') + ":" + sec.toString().padStart(2, '0');
            } else {
                return min + ":" + sec.toString().padStart(2, '0');
            }
        },

        seek: function (sec) {
            if (player) {
                player.seekTo(sec, true);
            }
        },

        dbDateTime2localDateTime: function (dbDateTime) {
            return new Date(dbDateTime).toLocaleDateString('sv-SE');
        }
    }));
});

let body = document.querySelector("body");

let term = urlQuery.get('q');
if (term) {
    var event1 = new Promise(function(resolve) {
        body.addEventListener("term_requested",resolve,false);
    })
    var event2 = new Promise(function(resolve) {
        body.addEventListener("youtube_loaded", resolve, false);
    })
    Promise.all([event1, event2]).then(function() {
        body.dispatchEvent(new Event('search_term'));
    });

    document.addEventListener('alpine:initialized', () => {
        body.dispatchEvent(new Event('term_requested'));
    })
}

function onYouTubeIframeAPIReady() {
    player = new YT.Player(
        'player2',
        {
            events: {
                'onReady': onPlayerReady,
                'onStateChange': onPlayerStateChange,
            }
        },
    );
}
let loaded_done = false;
function onPlayerReady(event) {
    body.dispatchEvent(new Event('search_term'));
    loaded_done = true;
}
function onPlayerStateChange(event) {
    // console.log(event.data);
    if (
        (event.data == YT.PlayerState.PLAYING)
        || (event.data == YT.PlayerState.PAUSED)
        || (event.data == YT.PlayerState.BUFFERING)
        || (event.data == YT.PlayerState.ENDED)
    ) {
        body.dispatchEvent(
            new CustomEvent(
                'youtube_updated', {
                    detail: {
                        "state": event.data,
                        "time": player.getCurrentTime(),
                    }
                }
            )
        );
    }
}

document.addEventListener('keydown', function (e) {
    if (e.target.classList.contains("uk-input")) {
        return;
    }
    if (loaded_done == false) {
        return;
    }
    let second = parseInt(document.querySelector("input[name=forward_sec]").value);
    // console.log(e.key);
    let ts = player.getCurrentTime();
    if (e.key == "ArrowLeft") {
        player.seekTo(ts - second, true);
        body.dispatchEvent(new Event('youtube_manually_moved'));
    } else if (e.key == "ArrowRight") {
        player.seekTo(ts + second, true);
        body.dispatchEvent(new Event('youtube_manually_moved'));
    } else if (e.key == " ") {
        if (player.getPlayerState() == YT.PlayerState.PLAYING) {
            player.pauseVideo();
        } else {
            player.playVideo();
        }
        e.preventDefault();
    }
});
