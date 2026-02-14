import os
from llama_index.core import (
    SimpleDirectoryReader, 
    VectorStoreIndex, 
    StorageContext,
    load_index_from_storage
)


class LlamaDocuments:
    """
    Clase para manejar documentos con LlamaIndex.
    Carga documentos, crea índices y permite consultas.
    """

    def __init__(self, directory: str, storage_dir: str = "./storage"):
        """
        Args:
            directory: Carpeta con los documentos (PDFs, TXTs, etc.)
            storage_dir: Carpeta donde persistir el índice
        """
        self.directory = directory
        self.storage_dir = storage_dir
        self.index = None
        self.query_engine = None
    
    def _existe_storage(self) -> bool:
        """Verifica si ya existe un índice guardado."""
        return os.path.exists(self.storage_dir) and os.path.exists(
            os.path.join(self.storage_dir, "docstore.json")
        )
    
    def _cargar_documentos(self):
        """Lee archivos del directorio y los convierte a documentos."""
        documents = SimpleDirectoryReader(self.directory).load_data()
        print(f"Documentos cargados: {len(documents)} archivos desde '{self.directory}'")
        return documents
    
    def _crear_indice(self, documents):
        """Crea índice vectorial a partir de documentos."""
        self.index = VectorStoreIndex.from_documents(documents)
        print("Índice vectorial creado exitosamente")
    
    def _persistir_indice(self):
        """Guarda el índice en disco para reutilizar."""
        self.index.storage_context.persist(persist_dir=self.storage_dir)
        print(f"Índice persistido en '{self.storage_dir}'")
    
    def _cargar_desde_storage(self):
        """Carga índice previamente guardado."""
        storage_context = StorageContext(persist_dir=self.storage_dir)
        self.index = load_index_from_storage(storage_context)
        print(f"Índice cargado desde '{self.storage_dir}'")
    
    def inicializar(self):
        """
        Inicializa el índice:
        - Si existe storage: carga el índice guardado
        - Si no existe: carga documentos → crea índice → guarda
        
        Returns:
            self (para encadenar métodos)
        """
        if self._existe_storage():
            print("Storage encontrado, cargando índice existente...")
            self._cargar_desde_storage()
        else:
            print("Storage no encontrado, creando nuevo índice...")
            documents = self._cargar_documentos()
            self._crear_indice(documents)
            self._persistir_indice()
        
        # Crear query engine para consultas
        self.query_engine = self.index.as_query_engine()
        print("Query engine listo para consultas")
        
        return self
    
    def consultar(self, query: str) -> str:
        """
        Realiza una consulta al índice.
        
        Args:
            query: Pregunta del usuario
            
        Returns:
            Respuesta generada por el LLM basada en los documentos
        """
        if not self.query_engine:
            raise RuntimeError("Primero debes llamar inicializar()")
        
        response = self.query_engine.query(query)
        return str(response)
    
    def agregarDocumentos(self,nuevosDocs:str):
        """
        Agrega nuevos documentos al índice existente.
        
        Args:
            nuevosDocs: Ruta a la carpeta con nuevos documentos
            
        Returns:
            self (para encadenar métodos)
        """
        nuevos_documentos = SimpleDirectoryReader(nuevosDocs).load_data()
        print(f"Nuevos documentos cargados: {len(nuevos_documentos)} archivos desde '{nuevosDocs}'")
        
        # Agregar nuevos documentos al índice existente
        for doc in nuevos_documentos:
            self.index.insert(doc)
        
        # Persistir el índice actualizado
        self._persistir_indice()
        
        return self