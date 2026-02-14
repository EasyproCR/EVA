import React from "react";
import RobotImage from "../assets/images/RobotImage.png";
import { motion } from "motion/react";
function Robot({estatico}){
    return(
        estatico ? (
            <div className="robot-container ">
                <img src={RobotImage} alt="Robot" className="robot-image"/>
            </div>
        ) : ( 
            <motion.div animate={{ y: [0, -20, 0]}} transition={{ repeat: Infinity, duration: 2 }} style={{ scale: 1.5 }} className="robot-container ">
                <img src={RobotImage} alt="Robot" className="robot-image" />
            </motion.div>
        )
    );

}
export default Robot;