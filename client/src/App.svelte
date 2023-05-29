<script>
  import { onMount } from 'svelte';

  let inputValue = "No text";
  let responseValue;

  async function sendData() {
    const response = await fetch('/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ value: inputValue })
    });
    const data = await response.text();
    responseValue = data;
  }

  let fileInput;
  let message = "No new files uploaded :)"

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
  }

  onMount(() => {
    sendData();
  });

  function handleFileChange(event) {
    fileInput = event.target;
    uploadFile();
  }

</script>

<h1>Unamed app 🕵️‍♂️</h1>
<input type="text" bind:value={inputValue}/>
<button on:click={sendData}>Submit</button>
<p>{responseValue}</p>


<form onsubmit="return false" enctype="multipart/form-data">
  <input type="file" on:change={handleFileChange}  multiple/>
</form>
<p>{message}</p>
