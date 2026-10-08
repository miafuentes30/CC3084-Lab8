-- Cuartiles exactos; una lista comparte el estado y reduce memoria.
WITH cuartiles AS (
    SELECT taxi, quantile_cont(total_amount, [0.25, 0.50, 0.75]) AS q
    FROM viajes_validos
    GROUP BY taxi
)
SELECT taxi, round(q[1], 2) AS q1, round(q[2], 2) AS mediana, round(q[3], 2) AS q3
FROM cuartiles
ORDER BY taxi
