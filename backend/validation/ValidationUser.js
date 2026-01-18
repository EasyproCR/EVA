export class ValidationUser {

    async determinarDepartamento(id){
        if(this.idRegex.test(id)){
            this.departamento = "Ventas";
        } else {
            this.departamento = "General";
        }

    }


}