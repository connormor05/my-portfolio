const fs = require("fs");
const path = require("path");

function loadCourses() {
  const filePath = path.join(__dirname, "..", "courses.json");
  const raw = fs.readFileSync(filePath, "utf8");
  return JSON.parse(raw);
}

module.exports = { loadCourses, };