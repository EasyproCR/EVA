export function bodyParserErrorHandler({ maxBodySize }) {
    return (err, req, res, next) => {
        if (err && err.type === "entity.too.large") {
            return res.status(413).json({ error: `Payload demasiado grande (límite ${maxBodySize})` });
        }
        if (err instanceof SyntaxError) {
            return res.status(400).json({ error: "JSON inválido" });
        }
        next(err);
    };
}
