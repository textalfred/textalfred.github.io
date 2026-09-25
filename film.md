---
layout: page
data_key: film
title: "The film."
permalink: /film.html
---

{{ site.data.alfred.film.intro }}

<figure class="film">
  <video controls playsinline preload="metadata" poster="{{ '/assets/film/alfred-film-poster.jpg' | relative_url }}" width="1920" height="1080">
    <source src="{{ '/assets/film/alfred-film.mp4' | relative_url }}" type="video/mp4">
    <a href="{{ '/assets/film/alfred-film.mp4' | relative_url }}">Download the film (MP4, 3 MB)</a>
  </video>
</figure>
