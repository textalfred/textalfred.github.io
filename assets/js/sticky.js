// Mobile-only sticky "join the waitlist" bar (CSS hides it above 600px).
// Hidden while any other CTA or the form is on screen, and after a successful submit.
(function () {
  var bar = document.querySelector('.sticky-cta');
  if (!bar || !('IntersectionObserver' in window)) return;
  var targets = document.querySelectorAll('.cta-line, #waitlist');
  var seen = new Set();
  var done = false;
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { e.isIntersecting ? seen.add(e.target) : seen.delete(e.target); });
    bar.hidden = done || seen.size > 0;
  });
  targets.forEach(function (t) { io.observe(t); });
  var form = document.getElementById('waitlist');
  if (form) form.addEventListener('submit', function () {
    var ok = form.querySelector('[data-fs-success]');
    new MutationObserver(function () {
      if (ok && ok.hasAttribute('data-fs-active')) { done = true; bar.hidden = true; }
    }).observe(form, { attributes: true, subtree: true });
  });
})();
