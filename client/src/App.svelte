<script>
  import { onMount } from 'svelte';
  let rand = -1;
  let input_text = "nothing";
  function getRand() {
    fetch("./hello")
      .then(d => d.text())
      .then(d => (rand = d));
  }

  let inputValue = '';
  let responseValue = '';

  async function sendData() {
    const response = await fetch('/print_value', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ value: inputValue })
    });
    const data = await response.text();
    responseValue = data;
  }

  onMount(() => {
    sendData();
  });

</script>

<h1>Unamed app</h1>
<input type="text" bind:value={inputValue} />
<button on:click={sendData}>Submit</button>
<p>{responseValue}</p>