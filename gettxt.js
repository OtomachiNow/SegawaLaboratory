const response = await fetch("./nisi.txt");
const text = await response.text();
export default text;