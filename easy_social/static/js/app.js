(function () {
  function mediaKind(file) {
    if (file.type.startsWith("image/")) {
      return "image";
    }
    if (file.type.startsWith("video/")) {
      return "video";
    }

    const extension = file.name.split(".").pop().toLowerCase();
    if (["gif", "jpg", "jpeg", "png", "webp"].includes(extension)) {
      return "image";
    }
    if (["mov", "mp4", "ogg", "webm"].includes(extension)) {
      return "video";
    }
    return "";
  }

  function clearPreview(preview, frame, name, input, state) {
    if (state.objectUrl) {
      URL.revokeObjectURL(state.objectUrl);
      state.objectUrl = "";
    }
    frame.replaceChildren();
    name.textContent = "";
    preview.hidden = true;
    if (input) {
      input.value = "";
    }
  }

  function setupComposerType(composer, mediaInput, preview, frame, name, state) {
    const pollOptions = composer.querySelector("[data-poll-options]");
    const mediaPicker = composer.querySelector("[data-composer-media]");
    const body = composer.querySelector("[data-composer-body]");
    const typeInputs = composer.querySelectorAll("[data-post-type]");

    if (!pollOptions || !typeInputs.length) {
      return;
    }

    function updateComposerMode() {
      const selected = composer.querySelector("[data-post-type]:checked");
      const isPoll = selected && selected.value === "poll";
      pollOptions.hidden = !isPoll;
      if (mediaPicker) {
        mediaPicker.hidden = isPoll;
        if (mediaInput) {
          mediaInput.disabled = isPoll;
        }
        if (isPoll && preview && frame && name) {
          clearPreview(preview, frame, name, mediaInput, state);
        }
      }
      if (body) {
        body.placeholder = isPoll ? "Ask a question for your poll" : "What is happening?";
      }
      pollOptions.querySelectorAll("[data-poll-required]").forEach(function (field) {
        field.required = isPoll;
      });
    }

    typeInputs.forEach(function (input) {
      input.addEventListener("change", updateComposerMode);
    });
    updateComposerMode();
  }

  function setupComposer(composer) {
    const input = composer.querySelector("[data-media-input]");
    const preview = composer.querySelector("[data-media-preview]");
    const frame = composer.querySelector("[data-media-preview-frame]");
    const name = composer.querySelector("[data-media-preview-name]");
    const clear = composer.querySelector("[data-media-preview-clear]");
    const state = { objectUrl: "" };

    if (!input || !preview || !frame || !name) {
      return;
    }

    setupComposerType(composer, input, preview, frame, name, state);

    input.addEventListener("change", function () {
      const file = input.files && input.files[0];
      clearPreview(preview, frame, name, null, state);

      if (!file) {
        return;
      }

      const kind = mediaKind(file);
      if (!kind) {
        return;
      }

      state.objectUrl = URL.createObjectURL(file);
      const element = document.createElement(kind === "image" ? "img" : "video");
      element.className = "composer-preview-media";
      element.src = state.objectUrl;

      if (kind === "image") {
        element.alt = "Selected image preview";
      } else {
        element.controls = true;
        element.muted = true;
        element.preload = "metadata";
      }

      frame.replaceChildren(element);
      name.textContent = file.name;
      preview.hidden = false;
    });

    if (clear) {
      clear.addEventListener("click", function () {
        clearPreview(preview, frame, name, input, state);
        input.dispatchEvent(new Event("change", { bubbles: true }));
      });
    }
  }

  function setupCaptchaRefresh(button) {
    const image = document.getElementById("captcha-image");
    if (!image) {
      return;
    }

    button.addEventListener("click", function () {
      const url = new URL(image.src, window.location.origin);
      url.searchParams.set("t", String(Date.now()));
      image.src = url.toString();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("form.composer").forEach(setupComposer);
    document.querySelectorAll("[data-captcha-refresh]").forEach(setupCaptchaRefresh);
  });
})();
