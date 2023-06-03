<script>
  import { onMount } from 'svelte';
  import History from './lib/History.svelte';
  let inputValue = "";
  let responseValue = "";
  let indexedInfo = "";
  let token = "";

  let historylist = [];

  async function getHistoryList() {
    const response = await fetch(`/app/get_history_list/${token}`);
    const data = await response.json();

    if (response.ok) {
      historylist = data.queries;
    } else {
      historylist = ["Could not load history"];
    }
  }

  async function getTokenFromUrl() {
    const path = window.location.pathname;
    const parts = path.split("/");
    const lastPart = parts[parts.length - 1];
    token = lastPart;
  }

  async function getUploadedItems() {
    const response = await fetch(`./get_uploaded_count/${token}`);
    const data = await response.text();
    return data;
  }

  async function fetchData() {
    const count = await getUploadedItems();
    if (count === "0") {
      indexedInfo = "Upload files to get started!";
      return;
    } else if (count === "1") {
      indexedInfo = count + " file indexed";
      return;
    }
    indexedInfo = count + " files indexed.";
  }

  async function search() {
    if (inputValue === "") {
      responseValue = "No text :(";
      return;
    }
    responseValue = "Loading...";

    const response = await fetch(`./search/${token}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ value: inputValue })
    });
    const data = await response.json();
    responseValue = data.result;
    await getHistoryList();
  }

  let fileInput;

  async function uploadFile() {
    indexedInfo = "Uploading...";

    const formData = new FormData();

    const allowedFileTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml', 'image/webp'];
    let unsupportedFiles = [];

    for (let i = 0; i < fileInput.files.length; i++) {
      if (allowedFileTypes.includes(fileInput.files[i].type)) {
        unsupportedFiles.push(fileInput.files[i].name);
        continue;
      }
      formData.append('files[]', fileInput.files[i]);
    }

    const response = await fetch(`./upload_file/${token}`, {
      method: 'POST',
      body: formData
    });

    if (unsupportedFiles.length > 0) {
      const warningMessage = `Could not upload the following files. Image type files are not allowed: ${unsupportedFiles.join(', ')}`;
      alert(warningMessage);
    }

    const data = await response.json();
    fetchData();
  }

  function handleKeyDown(event) {
    if (event.key === "Enter") {
      search();
    }
  }

  function handleFileChange(event) {
    fileInput = event.target;
    uploadFile();
  }


  onMount(async () => {
    await getTokenFromUrl();
    await fetchData();
    await getHistoryList();
  });

</script>

<div class="row">
      <History historyList={historylist} />
</div>

    <div class="row-bar">
      <div class="top-bar">
        <h1>inhouse 🏠</h1>
        <div class="search-container">
          <div class="input-container">
            <input placeholder="Ask a question." class="searchbar" type="text" bind:value={inputValue} on:keydown={handleKeyDown}/>
            <button class="submit-button" on:click={search}>🔍</button>
          </div>
          <div class="upload-button-container">
            <label for="fileInput" class="upload-button">
              📥  &thinsp; Upload
              <input id="fileInput" type="file" style="display:none" on:change={handleFileChange} multiple />
            </label>
          </div>
        </div>
        <p class="custom-i">{indexedInfo}</p>
      </div>

      <p>{responseValue}</p>

    </div>
    
