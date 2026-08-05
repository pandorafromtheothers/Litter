const bookpopularity = 100000;
    function numberAbbriavte(result) {
      return Intl.NumberFormat('en-US', { notation: "compact", maximumFractionDigits: result < 10000 ? 1 : 0 }).format(result);
    }
    document.addEventListener('DOMContentLoaded', () => {
      document.querySelectorAll('.tweet-card').forEach((card) => {
        const stats = card.querySelector('.tweet-stats');
        if (!stats) return;

        let tweetpopularity = Math.random() >= 5 ? bookpopularity : Math.floor(Math.random() * (bookpopularity));

        let comments = Math.floor(Math.random() * tweetpopularity);
        comments = tweetpopularity >= 10000 ? Math.floor(comments % (tweetpopularity / 100)) : comments;

        const retweets = Math.floor(Math.random() * tweetpopularity);
        const likes = Math.floor(Math.random() * tweetpopularity) + retweets;
        const views = Math.floor(Math.random() * tweetpopularity) + comments + retweets + likes;

        const spans = stats.querySelectorAll('span');
        if (spans.length >= 1) spans[0].append(`${numberAbbriavte(comments)}`);
        if (spans.length >= 2) spans[1].append(`${numberAbbriavte(retweets)}`);
        if (spans.length >= 3) spans[2].append(`${numberAbbriavte(likes)}`);
        if (spans.length >= 4) spans[3].append(`${numberAbbriavte(views)}`);
      });
    });
    document.addEventListener("click", (element) => {
      let parent = element.target.closest(".tweet-stat-flex");
      if (parent == undefined)
        return;
      if (!parent.classList.toString().includes("heart"))
        return;

      if (!parent.querySelector("input").checked) {
        parent.querySelector(".empty-heart").classList.add("hide");
        parent.querySelector(".full-heart").classList.remove("hide");
        parent.querySelector(".full-heart").classList.add("heart-checked");
        parent.querySelector("input").checked = true;
      }
      else {
        parent.querySelector(".empty-heart").classList.remove("hide");
        parent.querySelector(".full-heart").classList.remove("heart-checked");
        parent.querySelector(".full-heart").classList.add("hide");
        parent.querySelector("input").checked = false;
      }

    });
    document.addEventListener("click", (element) => {
      let parent = element.target.closest(".tweet-stat-flex");
      if (parent == undefined)
        return;
      if (!parent.classList.toString().includes("retweets"))
        return;

      if (!parent.querySelector("input").checked) {
        parent.querySelector(".retweets").classList.add("retweet-checked");
        parent.classList.add("retweet-checked");
        parent.querySelector("input").checked = true;
      }
      else {
        parent.querySelector(".retweets").classList.remove("retweet-checked");
        parent.classList.remove("retweet-checked");
        parent.querySelector("input").checked = false;
      }

    });