// Check if MetaMask is installed
if (typeof window.ethereum !== 'undefined') {
  console.log('MetaMask is installed!');
} else {
  alert('Please install MetaMask to use this dApp!');
}

const connectWalletButton = document.getElementById('connectWallet');
const statusDiv = document.getElementById('status');

connectWalletButton.addEventListener('click', async () => {
  try {
    // Request account access
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    const account = accounts[0];
    statusDiv.innerText = `Connected account: ${account}`;

    // Initialize Web3
    const web3 = new Web3(window.ethereum);

    // Replace with your contract's ABI and address
    const contractABI = [ /* Your Contract ABI */ ];
    const contractAddress = '0xYourContractAddress';

    const contract = new web3.eth.Contract(contractABI, contractAddress);

    // Example: Call a function from your contract
    // const data = await contract.methods.yourMethod().call();
    // console.log(data);

  } catch (error) {
    console.error(error);
    statusDiv.innerText = 'Error connecting to MetaMask.';
  }
});
