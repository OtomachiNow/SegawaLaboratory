(function (global) {
    "use strict";

    function renderRichText(text) {
        if (!text) return "";
        return String(text).split(/(\$\$[\s\S]*?\$\$)/g).map(function (part) {
            if (part.startsWith("$$") && part.endsWith("$$")) return part;
            return part.replace(/\n/g, "<br>");
        }).join("");
    }

    function render(article, container, speakers) {
        if (!container) throw new Error("Article container is required.");
        speakers = speakers || {};
        container.innerHTML = "";
        var isNovel = article && article.type === "novel";
        container.classList.toggle("novel-mode", isNovel);

        function renderElements(elements, target) {
            (elements || []).forEach(function (item) {
                if (item.type === "dialogue") {
                    if (isNovel) {
                        var novel = document.createElement("p");
                        novel.className = "novel-text";
                        novel.innerHTML = item.content || "";
                        target.appendChild(novel);
                        return;
                    }
                    var row = document.createElement("div");
                    row.className = "dialogue-row " + (item.side || "left");
                    var speakerKey = String(item.speaker || "").trim();
                    var profile = speakers[speakerKey] || { color: "#f0f0f0", icon: "" };
                    var icon = document.createElement("div");
                    icon.className = "icon";
                    if (profile.icon) {
                        icon.style.backgroundImage = "url(" + profile.icon + ")";
                    } else {
                        icon.textContent = speakerKey.charAt(0);
                    }
                    icon.style.backgroundColor = profile.color || "#f0f0f0";
                    var bubble = document.createElement("div");
                    bubble.className = "bubble";
                    bubble.innerHTML = item.content || "";
                    if (profile.color) bubble.style.backgroundColor = profile.color;
                    row.appendChild(icon);
                    row.appendChild(bubble);
                    target.appendChild(row);
                } else if (item.type === "heading") {
                    var heading = document.createElement("h2");
                    heading.className = "section-heading";
                    heading.textContent = item.content || "";
                    target.appendChild(heading);
                } else if (item.type === "text") {
                    var paragraph = document.createElement("p");
                    paragraph.className = isNovel ? "novel-text" : "narrative-text";
                    paragraph.innerHTML = item.content || "";
                    target.appendChild(paragraph);
                } else if (item.type === "math") {
                    var math = document.createElement("div");
                    math.className = "article-math";
                    math.innerHTML = item.content || "";
                    target.appendChild(math);
                } else if (item.type === "code") {
                    var pre = document.createElement("pre");
                    var code = document.createElement("code");
                    if (item.language) code.className = "language-" + item.language;
                    code.textContent = item.content || "";
                    pre.appendChild(code);
                    target.appendChild(pre);
                } else if (item.type === "image") {
                    var figure = document.createElement("figure");
                    figure.className = "article-image";
                    var image = document.createElement("img");
                    image.src = item.src || "";
                    image.alt = item.caption || "";
                    figure.appendChild(image);
                    if (item.caption) {
                        var caption = document.createElement("figcaption");
                        caption.innerHTML = renderRichText(item.caption);
                        figure.appendChild(caption);
                    }
                    target.appendChild(figure);
                } else if (item.type === "box") {
                    var box = document.createElement("div");
                    box.className = "article-box";
                    var titleText = item.title || "";
                    if (titleText.includes("定義")) box.classList.add("box-def");
                    else if (titleText.includes("定理")) box.classList.add("box-thm");
                    else if (titleText.includes("証明")) box.classList.add("box-proof");
                    else if (titleText.includes("まとめ")) box.classList.add("box-summary");
                    else if (titleText.includes("宿題")) box.classList.add("box-hw");
                    if (titleText) {
                        var boxTitle = document.createElement("div");
                        boxTitle.className = "box-title";
                        boxTitle.innerHTML = renderRichText(titleText);
                        box.appendChild(boxTitle);
                    }
                    var boxBody = document.createElement("div");
                    boxBody.className = "box-body";
                    if (item.children) renderElements(item.children, boxBody);
                    else boxBody.innerHTML = renderRichText(item.content);
                    box.appendChild(boxBody);
                    target.appendChild(box);
                } else if (item.type === "fold") {
                    var details = document.createElement("details");
                    var summary = document.createElement("summary");
                    summary.innerHTML = renderRichText(item.summary || "詳細を表示");
                    details.appendChild(summary);
                    var foldBody = document.createElement("div");
                    foldBody.className = "fold-body";
                    if (item.children) renderElements(item.children, foldBody);
                    else foldBody.innerHTML = renderRichText(item.content);
                    details.appendChild(foldBody);
                    target.appendChild(details);
                } else if (item.type === "truth") {
                    var table = document.createElement("table");
                    table.className = "truth-table";
                    (item.rows || []).forEach(function (cells, rowIndex) {
                        var tr = document.createElement("tr");
                        cells.forEach(function (cellText) {
                            var cell = document.createElement(rowIndex === 0 ? "th" : "td");
                            cell.innerHTML = cellText;
                            tr.appendChild(cell);
                        });
                        table.appendChild(tr);
                    });
                    target.appendChild(table);
                }
            });
        }

        renderElements((article && article.data) || [], container);
        return container;
    }

    global.SegawaArticleRenderer = { render: render, renderRichText: renderRichText };
})(window);

