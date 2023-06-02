
<script>


let history = "History";
let dummyList = ["How many invoices do I have?", "Who are my biggest competitors?", "What does my insurance protect me against?", "When is my next payment due?"];



    /* ---
    import { getContext } from 'svelte';

    const submitQuestion = getContext('submitQuestion');
    const historicQuestions = getContext('historicQuestions');

    --- */ 

    /*
    let history = "History";


    
    let dummyList = ["How many invoices do I have?", "Who are my biggest competitors?", "What does my insurance protect me against?", "When is my next payment due?"];

    /*
    async function fetchHistoricRecord(){

      const response = await fetch("./get_history");

		  sideBarList = response

    }
    */

  </script>

<div class="wrapper">
  <h3>{history}</h3>

  <div class="list-container">
    {#each dummyList as item}
      <div class="history-item">{item}</div>
    {/each}
  </div>
</div>




<!--


<div class="wrapper">
  <div class="title">{history}</div>

    <div class="list-container">

      {#each dummyList as question}

        <div class="history-item">📄 &nbsp; {question}</div>

      {/each}

    </div>
  </div>
-->

