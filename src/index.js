const express = require("express");
const http = require("http");
const https = require("https");
const { Server } = require("socket.io");
const compression = require("compression");
const { exec } = require("child_process");
const { createHash } = require("crypto");
const {
  writeFileSync,
  readFileSync,
  existsSync,
  mkdirSync,
  truncateSync,
  createReadStream,
  createWriteStream,
} = require("fs");
const { join } = require("path");

const app = express();
const server = http.createServer(app);
const io = new Server(server);
const server_location = join(__dirname, "..", "minecraft_server");
const server_setting = join(server_location, "..", "SERVER.settings");
const log_path = join(server_location, "..", "log.txt");
let server_execute;

if (!existsSync(server_location)) mkdirSync(server_location);
if (!existsSync(log_path)) writeFileSync(log_path, "");

const log = createWriteStream(log_path, {
  flags: "a",
});

const log_write = (buf) => {
  if (!Buffer.isBuffer(buf)) io.emit("log", buf);
  log.write(buf);
};
log.info = (message, type = "SYSTEM") => {
  const d = new Date();
  const _d = (n) => n.toString().padStart(2, "0");
  log_write(
    `[${_d(d.getHours())}:${_d(d.getMinutes())}:${_d(
      d.getSeconds()
    )} ${type}]: ${message}\n`
  );
};

app.use("/assets/", express.static(join(__dirname, "..", "assets")));
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(compression({ level: 9 }));

async function handleFileCache(req, res, filepath) {
  const hash = createHash("md5");
  const stream = createReadStream(filepath);

  stream.on("data", (chunk) => hash.update(chunk));
  stream.on("end", async () => {
    const etag = hash.digest("hex");
    res.setHeader("Cache-Control", "public, max-age=31536000");
    res.setHeader("ETag", etag);

    if (req.headers["if-none-match"] === etag) {
      res.status(304).end();
    } else {
      res.sendFile(filepath);
    }
  });
  stream.on("error", () => res.status(500).send());
}

function download_file(url, filename, cb) {
  log.info(url);
  https.get(url, (res) => {
    if (res.statusCode == 200) {
      const file = createWriteStream(join(server_location, filename));
      res.pipe(file);
      file.on("finish", () => {
        file.close();
        log.info("Download finished");
        if (cb) cb();
      });
    } else {
      log.info("Download failed");
    }
  });
}

function is_installed() {
  if(!existsSync(server_setting)) return false;
  const setting = readFileSync(
    server_setting,
    "utf8"
  );
  let executable = setting.match(/executable=(.+)/);
  executable = executable ? executable[1] : null;
  if(!executable || !existsSync(executable)) return false;
  return true;
}

async function get_versions(type = "paper") {
  if (!["paper", "purpur"].includes(type)) throw Error("Invalid server type!");

  let versions = [];
  switch (type) {
    case "paper":
      const json = await (
        await fetch("https://api.papermc.io/v2/projects/paper")
      ).json();
      versions = json.versions.reverse();
      return versions;
    case "purpur":
      const html = await (
        await fetch("https://purpurmc.org/download/purpur/")
      ).text();
      versions = (html.match(/option value="([^"]+)/g) ?? []).map((e) =>
        e.replace('option value="', "")
      );
      return versions;
    default:
      return versions;
  }
}

async function get_jar_download_url(type = "paper", version = "") {
  if (!["paper", "purpur"].includes(type)) throw Error("Invalid server type!");

  let url = "";
  switch (type) {
    case "paper":
      const _builds = await (
        await fetch(
          `https://api.papermc.io/v2/projects/paper/versions/${version}/builds`
        )
      ).json();
      const latestBuild = _builds.builds.at(-1);
      url = `https://api.papermc.io/v2/projects/paper/versions/${version}/builds/${latestBuild.build}/downloads/${latestBuild.downloads.application.name}`;
      return url;
    case "purpur":
      const release = await (
        await fetch(`https://purpurmc.org/download/purpur/${version}`)
      ).text();
      const mver = release.match(
        /href="https:\/\/api\.purpurmc\.org\/v2\/purpur\/([^\/]+)\/([^\/]+)\/download"/
      );
      if (mver) {
        const [_, ver, bver] = mver;
        url = `https://api.purpurmc.org/v2/purpur/${ver}/${bver}/download`;
      }
      return url;
    default:
      return url;
  }
}

async function install_server(type = "paper", version = "") {
  if (!["paper", "purpur"].includes(type)) throw Error("Invalid server type!");
  if(is_installed()) throw Error('Server already installed!');
  if (!version) {
    version = (await get_versions(type))[0];
  }

  const url = await get_jar_download_url(type, version);
  if (!url) throw Error(`Can't get jar file!`);
  log.info("Getting ready for install server");
  writeFileSync(
    server_setting,
    `executable=${type}.jar\nserver-type=${type}\nmin-memory=128M\nmax-memory=3G\n`
  );
  download_file(url, `${type}.jar`, () => {
    writeFileSync(join(server_location, "eula.txt"), "eula=true");
  });
}

function start_server() {
  if(!is_installed()) throw Error('Server not installed!');
  const setting = readFileSync(
    server_setting,
    "utf8"
  );
  let executable = setting.match(/executable=(.+)/);
  executable = executable ? executable[1] : null;
  let min_memory = setting.match(/min-memory=(.+)/);
  min_memory = min_memory ? min_memory[1] : "1M";
  let max_memory = setting.match(/max-memory=(.+)/);
  max_memory = max_memory ? max_memory[1] : "2G";

  if (!executable) throw Error("Missing server executable!");
  log.info("Starting server...");

  if (server_execute) throw Error("Server already running!");
  server_execute = exec(
    `java -Xms${min_memory} -Xmx${max_memory} -jar ${executable} --nogui`,
    { cwd: server_location, detached: true }
  );

  io.emit("status", !server_execute ? false : true);
  server_execute.stdout.on("data", (d) => {
    log_write(d.toString().replace(/\[(\d+;?){1,9}m/g, ""));
  });
  server_execute.stderr.on("data", (d) => {
    log_write(d.toString().replace(/\[(\d+;?){1,9}m/g, ""));
  });
  server_execute.on("close", () => {
    log.info("Server stopped");
    server_execute = null;
  });
}

function stop_server() {
  if (!server_execute) throw Error("No running server!");
  log.info("Stoping server...");
  (async () => {
    try {
      const fkill = (await import("fkill")).default;
      await fkill(server_execute.pid, { force: true });
      io.emit("status", !server_execute ? false : true);
    } catch (err) {
      log.info("Failed stopping server");
    }
  })();
}

function restart_server() {
  if (!server_execute) return start_server();

  (async () => {
    try {
      log.info("Re-starting server...");
      const fkill = (await import("fkill")).default;
      await fkill(server_execute.pid, { force: true });
      io.emit("status", !server_execute ? false : true);
      start_server();
    } catch (err) {
      log.info("Failed stopping server");
    }
  })();
}

function run_command(cmd) {
  if (!server_execute) throw Error("No running server!");
  server_execute.stdin.write(`${cmd}\n`);
  log.info(`> ${cmd}`, 'COMMAND');
}

app.get("/version/:server", async function (req, res) {
  try {
    const versions = await get_versions(req.params.server);
    return res.status(200).json({ status: "OK", code: 200, versions });
  } catch (err) {
    return res.sendStatus(500);
  }
});

app.get("/install/:server/:version", async function (req, res) {
  console.log(req.params);
  const { server, version } = req.params;
  if (existsSync("SERVER.settings"))
    return res.status(400).json({
      status: "ERROR",
      code: 400,
      message: "Server already installed",
    });
  install_server(server, version);
  res.sendStatus(200);
});

app.get("/start", async function (req, res) {
  try {
    start_server();
    return res.status(200).json({ status: "OK", code: 200 });
  } catch (err) {
    return res
      .status(500)
      .json({ status: "ERROR", code: 500, message: err.toString() });
  }
});

app.get("/stop", async function (req, res) {
  try {
    stop_server();
    return res.status(200).json({ status: "OK", code: 200 });
  } catch (err) {
    return res
      .status(500)
      .json({ status: "ERROR", code: 500, message: err.toString() });
  }
});

app.get("/restart", async function (req, res) {
  try {
    restart_server();
    return res.status(200).json({ status: "OK", code: 200 });
  } catch (err) {
    return res
      .status(500)
      .json({ status: "ERROR", code: 500, message: err.toString() });
  }
});

app.get("/clear-log", async function (req, res) {
  try {
    truncateSync(log_path);
    io.emit("clear");
    return res.status(200).json({ status: "OK", code: 200 });
  } catch (err) {
    return res
      .status(500)
      .json({ status: "ERROR", code: 500, message: err.toString() });
  }
});

app.get("/run-command", async function (req, res) {
  try {
    const { command } = req.query;
    if (!command)
      return res.status(400).json({
        status: "ERROR",
        code: 400,
        message: "command can't be empty!",
      });
    run_command(command);
    return res.status(200).json({ status: "OK", code: 200 });
  } catch (err) {
    return res
      .status(500)
      .json({ status: "ERROR", code: 500, message: err.toString() });
  }
});

io.on("connection", (socket) => {
  socket.emit("log", readFileSync(log_path, "utf8"));
  socket.emit("status", !server_execute ? false : true);
});

app.get("/", (req, res) => {
  handleFileCache(req, res, join(__dirname, "..", "public", "index.html"));
});

server.listen(3000, () => console.log("Server running on port 3000"));
