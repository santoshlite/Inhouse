<script>
  import { onMount } from 'svelte';
  import History from './lib/History.svelte'

  let inputValue = "";
  let responseValue = "";
  let indexedInfo = "";

  async function getUploadedItems() {
    const response = await fetch("./get_uploaded_count");
    const data = await response.text();
    return data;
  }

  async function fetchData() {
    const count = await getUploadedItems();
    if(count === "1" || count === "0" ){
      indexedInfo = count + " item indexed";
      return
    }
    indexedInfo = count + " items indexed.";
  }

  async function sendData() {
    if (inputValue === "") {
      responseValue = "No text :(";
      return
    }

    responseValue = "Loading...";

    const response = await fetch('/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ value: inputValue })
    });
    const data = await response.json();
    responseValue = data.result;
  }

  let fileInput;
  let message = ""

  async function uploadFile() {
    message = "Uploading..."

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
    const response = await fetch('/upload_file', {
      method: 'POST',
      body: formData
    });
    
    if (unsupportedFiles.length > 0) {
    const warningMessage = `Could not upload the following files. Image type files are not allowed: ${unsupportedFiles.join(', ')}`;
    alert(warningMessage);
  }

    const data = await response.json();
    message = data.Message;
    fetchData();
  }

  function handleFileChange(event) {
    fileInput = event.target;
    uploadFile();
  }

  onMount(() => {
    fetchData();
  });

</script>  

<div class="row">
  <History />
</div>

<div class="wrapper1">
  <div class="content-container">
    <h1>inhouse 🏠</h1>
    <input placeholder="Ask a question." class="searchbar" type="text" bind:value={inputValue}/>
    <button on:click={sendData}>Submit</button>

    <i class="custom-i"> {indexedInfo}</i>

    <p>{responseValue}</p>

    <h4>Upload new files</h4>
    <form onsubmit="return false" enctype="multipart/form-data">
      <input type="file" on:change={handleFileChange}  multiple/>
    </form>
    <p>{message}</p>
  </div>
</div>
