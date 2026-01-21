import { motion } from "motion/react";

function LoadingDots() {
    return (
        <div style={{display:"flex", gap:"10px"}} >
            {[0, 1, 2].map((dot) => (
                <motion.div
                    key={dot}
                    animate={{
                        scale:[1, 1.5, 1],
                        opacity:[0.6, 1, 0.6]
                    }}
                    transition={{
                        duration: 1,
                        repeat: Infinity,
                        delay: dot * 0.2,
                    }}
                    style={{
                        width: "15px",
                        height: "15px",
                        borderRadius: "50%",
                        backgroundColor: "#3498db",
                    }}
                />
            ))}
        </div>
    );
}
export default LoadingDots;