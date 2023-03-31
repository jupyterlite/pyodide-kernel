
<ul class="demo-links">
  <li>
    <label>
      <i class="fa-solid fa-external-link"></i>
      <i>Open in new tab</i>
    </label>
  </li>
  <li>
    <a href="./_static/lab/index.html?path=intro.ipynb" target="_blank" title="try JupyterLab, a multi-document app">
      <i class="fa-solid fa-flask"></i>
      Lab
    </a>
  </li>
  <li>
    <a href="./_static/retro/notebooks/index.html?path=intro.ipynb" target="_blank" title="try RetroLab, a single-document app">
      <i class="fa-solid fa-book"></i>
      Retro
    </a>
  </li>
  <li>
    <a href="./_static/repl/index.html?kernel=python&code=import%20this" target="_blank" title="try REPL, the minimal console app">
      <i class="fa-solid fa-terminal"></i>
      REPL
    </a>
  </li>
</ul>

<style>
  .demo-links {
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: row;
    list-style: none;
  }
  .demo-links li {
    list-style: none;
    flex: 0;
    text-align: right;
    white-space: nowrap;
    margin: 0 1em 0 1em;
  }
  .demo-links li:first-child {
    flex: 1;
  }
</style>

<iframe
    src="./_static/retro/notebooks/index.html?path=intro.ipynb"
    style="width: 99%; border: solid 1px #999; height: 500px"
></iframe>


```{include} ../README.md
```

## Learn More

```{toctree}
:maxdepth: 1

contributing.md
changelog.md
```
