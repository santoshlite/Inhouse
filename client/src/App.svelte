<script>
  import { onMount, setContext } from 'svelte';
  import History from './lib/History.svelte';

  /*
  // Create a reactive variable for historic questions
  import { writable } from 'svelte/store'; 
  const historicQuestions = writable([]);
  */

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
      indexedInfo = count + " file indexed";
      return
    }
    indexedInfo = count + " files indexed.";
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

    /*
    // Fetch the updated list of historic questions from the database
    const updatedQuestions = await fetchHistoricQuestions();

    // Update the reactive variable with the updated list of questions
    historicQuestions.set(updatedQuestions);

    */
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

  /*
  async function fetchHistoricQuestions() {
      // Fetch the historic questions from the database using the appropriate method
      // Return the list of questions
      const response = await fetch("./get_history");

		  return response
  }
  */

  onMount(() => {
    fetchData();
  });

  // Fetch the initial list of historic questions
  /*
  onMount(async () => {
    const questions = await fetchHistoricQuestions();
    historicQuestions.set(questions);
  });
  */

  // Pass down the submitQuestion function and historicQuestions variable to child components
  //setContext('submitQuestion', submitQuestion);
  //setContext('historicQuestions', historicQuestions);

</script>  




<!-- Render the child component -->


 <!-- 
  <History bind:fetchHistoricRecord={historyFunc} /> 
  --> 






<div class="row">
  <History />
</div>

    <div class="row-bar">
      <div class="top-bar">
        <h1>inhouse 🏠</h1>
        <div class="search-container">
          <div class="input-container">
            <input placeholder="Ask a question." class="searchbar" type="text" bind:value={inputValue}/>
            <button class="submit-button" on:click={sendData}>🔍</button>
            
            
            
            
            <!-- 
            
              Something that can be added to the buttons above!!!!!

              on:click={historyFunc.fetchHistoricRecord()} 
            
            -->





          </div>
        </div>
        <p class="custom-i">{indexedInfo}</p>
      </div>

      <p>{responseValue}</p>
      <h4>Upload new files</h4>
      <form onsubmit="return false" enctype="multipart/form-data">
        <input type="file" on:change={handleFileChange}  multiple/>
      </form>
      <p>{message}</p>
    </div>
    
